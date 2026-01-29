"""Tests for AI-assisted stored procedure rewriter."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.services.sp_rewriter_ai import (
    AIConfidenceLevel,
    AIRewriteResponse,
    AIRewriteAttempt,
    SQLValidationResult,
    AIResponseParser,
    SQLValidator,
    SPRewriterAI,
    ai_rewrite_sp,
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)
from app.services.sp_rewriter import (
    SPClassification,
    ConfidenceLevel,
    SPParameter,
)
from app.services.ollama_service import OllamaConfig, OllamaResult, OllamaMetrics


class TestAIConfidenceLevel:
    """Tests for AIConfidenceLevel enum."""

    def test_enum_values(self):
        """Test enum values."""
        assert AIConfidenceLevel.HIGH.value == "high"
        assert AIConfidenceLevel.MEDIUM.value == "medium"
        assert AIConfidenceLevel.LOW.value == "low"


class TestAIRewriteResponse:
    """Tests for AIRewriteResponse schema."""

    def test_basic_creation(self):
        """Test creating response."""
        response = AIRewriteResponse(
            sql_statement="SELECT * FROM users;",
            confidence=AIConfidenceLevel.HIGH,
            explanation="Simple conversion",
        )
        assert response.sql_statement == "SELECT * FROM users;"
        assert response.confidence == AIConfidenceLevel.HIGH
        assert response.explanation == "Simple conversion"


class TestAIRewriteAttempt:
    """Tests for AIRewriteAttempt schema."""

    def test_basic_creation(self):
        """Test creating attempt record."""
        attempt = AIRewriteAttempt(
            sp_name="sp_GetCustomers",
            sp_definition="CREATE PROCEDURE sp_GetCustomers AS SELECT * FROM customers",
        )
        assert attempt.sp_name == "sp_GetCustomers"
        assert attempt.method == "ai"
        assert attempt.is_valid is False

    def test_with_all_fields(self):
        """Test attempt with all fields."""
        attempt = AIRewriteAttempt(
            sp_name="sp_GetOrders",
            sp_definition="CREATE PROCEDURE sp_GetOrders AS SELECT * FROM orders",
            generated_sql="SELECT * FROM orders;",
            confidence=AIConfidenceLevel.HIGH,
            explanation="Simple conversion",
            is_valid=True,
            prompt_tokens=100,
            completion_tokens=50,
            duration_ms=3500,
        )
        assert attempt.generated_sql == "SELECT * FROM orders;"
        assert attempt.is_valid is True
        assert attempt.duration_ms == 3500


class TestSQLValidationResult:
    """Tests for SQLValidationResult schema."""

    def test_valid_result(self):
        """Test valid validation result."""
        result = SQLValidationResult(
            is_valid=True,
            is_select=True,
            has_snowflake_functions=True,
        )
        assert result.is_valid is True
        assert result.error_message is None

    def test_invalid_result(self):
        """Test invalid validation result."""
        result = SQLValidationResult(
            is_valid=False,
            error_message="Missing SELECT keyword",
        )
        assert result.is_valid is False
        assert "SELECT" in result.error_message


class TestAIResponseParser:
    """Tests for AIResponseParser."""

    def test_parse_standard_response(self):
        """Test parsing standard AI response format."""
        response = """
```sql
SELECT customer_id, customer_name
FROM customers
WHERE status = 'active';
```

Confidence: high

Explanation: Simple SELECT conversion with no function changes needed.
"""
        result = AIResponseParser.parse(response)
        assert result is not None
        assert "SELECT customer_id" in result.sql_statement
        assert result.confidence == AIConfidenceLevel.HIGH
        assert "Simple SELECT" in result.explanation

    def test_parse_without_code_fence(self):
        """Test parsing response without code blocks."""
        response = """
SELECT customer_id, customer_name
FROM customers
WHERE status = 'active';

Confidence: medium

Explanation: Converted without code fence.
"""
        result = AIResponseParser.parse(response)
        assert result is not None
        assert "SELECT customer_id" in result.sql_statement

    def test_parse_missing_confidence(self):
        """Test parsing response without confidence (defaults to medium)."""
        response = """
```sql
SELECT * FROM orders;
```

Explanation: Simple conversion.
"""
        result = AIResponseParser.parse(response)
        assert result is not None
        assert result.confidence == AIConfidenceLevel.MEDIUM

    def test_parse_empty_response(self):
        """Test parsing empty response."""
        result = AIResponseParser.parse("")
        assert result is None

    def test_parse_no_sql(self):
        """Test parsing response with no SQL."""
        response = "I cannot convert this stored procedure."
        result = AIResponseParser.parse(response)
        assert result is None

    def test_sql_semicolon_added(self):
        """Test that semicolon is added if missing."""
        response = """
```sql
SELECT * FROM users
```
"""
        result = AIResponseParser.parse(response)
        assert result is not None
        assert result.sql_statement.endswith(";")


class TestSQLValidator:
    """Tests for SQLValidator."""

    def test_valid_select(self):
        """Test valid SELECT statement."""
        sql = "SELECT * FROM users WHERE id = 1;"
        result = SQLValidator.validate(sql)
        assert result.is_valid is True
        assert result.is_select is True

    def test_empty_sql(self):
        """Test empty SQL."""
        result = SQLValidator.validate("")
        assert result.is_valid is False
        assert "Empty" in result.error_message

    def test_non_select(self):
        """Test non-SELECT statement."""
        sql = "UPDATE users SET name = 'test' WHERE id = 1;"
        result = SQLValidator.validate(sql)
        assert result.is_valid is False
        assert "SELECT" in result.error_message

    def test_unbalanced_parentheses(self):
        """Test unbalanced parentheses."""
        sql = "SELECT * FROM (SELECT id FROM users;"
        result = SQLValidator.validate(sql)
        assert result.is_valid is False
        assert "parentheses" in result.error_message.lower()

    def test_snowflake_functions_detected(self):
        """Test Snowflake function detection."""
        sql = "SELECT CURRENT_TIMESTAMP() as ts, COALESCE(name, 'N/A') FROM users;"
        result = SQLValidator.validate(sql)
        assert result.is_valid is True
        assert result.has_snowflake_functions is True

    def test_complex_valid_query(self):
        """Test complex but valid query."""
        sql = """
        SELECT
            u.user_id,
            u.name,
            COALESCE(o.order_count, 0) as orders,
            CURRENT_TIMESTAMP() as checked_at
        FROM users u
        LEFT JOIN (
            SELECT user_id, COUNT(*) as order_count
            FROM orders
            GROUP BY user_id
        ) o ON u.user_id = o.user_id
        WHERE u.status = 'active'
        ORDER BY u.name;
        """
        result = SQLValidator.validate(sql)
        assert result.is_valid is True
        assert result.is_select is True


class TestSPRewriterAI:
    """Tests for SPRewriterAI service."""

    @pytest.mark.asyncio
    async def test_rewrite_disabled_client(self):
        """Test rewrite when Ollama is disabled."""
        mock_client = MagicMock()
        mock_client.config = OllamaConfig(enabled=False)

        rewriter = SPRewriterAI(ollama_client=mock_client)
        result, attempt = await rewriter.rewrite(
            sp_name="sp_Test",
            sp_definition="CREATE PROCEDURE sp_Test AS SELECT 1",
            classification=SPClassification.MODERATE,
        )

        assert result.success is False
        assert "not enabled" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_rewrite_success(self):
        """Test successful AI rewrite."""
        mock_client = MagicMock()
        mock_client.config = OllamaConfig(enabled=True)

        # Mock successful AI response
        mock_result = OllamaResult(
            success=True,
            response="""
```sql
SELECT customer_id, customer_name
FROM customers
WHERE status = 'active';
```

Confidence: high

Explanation: Converted simple SELECT with no changes needed.
""",
            metrics=OllamaMetrics(
                request_time_ms=1000,
                prompt_tokens=200,
                completion_tokens=100,
                success=True,
            ),
        )

        mock_client.generate = AsyncMock(return_value=mock_result)

        rewriter = SPRewriterAI(ollama_client=mock_client)
        result, attempt = await rewriter.rewrite(
            sp_name="sp_GetCustomers",
            sp_definition="CREATE PROCEDURE sp_GetCustomers AS SELECT customer_id, customer_name FROM customers WHERE status = 'active'",
            classification=SPClassification.MODERATE,
        )

        assert result.success is True
        assert "customer_id" in result.converted_sql
        assert result.confidence == ConfidenceLevel.HIGH
        assert attempt.is_valid is True

    @pytest.mark.asyncio
    async def test_rewrite_ai_failure(self):
        """Test handling AI failure."""
        mock_client = MagicMock()
        mock_client.config = OllamaConfig(enabled=True)

        # Mock failed AI response
        mock_result = OllamaResult(
            success=False,
            error_message="Connection refused",
        )
        mock_client.generate = AsyncMock(return_value=mock_result)

        rewriter = SPRewriterAI(ollama_client=mock_client)
        result, attempt = await rewriter.rewrite(
            sp_name="sp_Test",
            sp_definition="CREATE PROCEDURE sp_Test AS SELECT 1",
            classification=SPClassification.MODERATE,
        )

        assert result.success is False
        assert "Connection" in result.error_message

    @pytest.mark.asyncio
    async def test_rewrite_parse_failure(self):
        """Test handling response parse failure."""
        mock_client = MagicMock()
        mock_client.config = OllamaConfig(enabled=True)

        # Mock response that cannot be parsed
        mock_result = OllamaResult(
            success=True,
            response="I don't understand this stored procedure.",
            metrics=OllamaMetrics(request_time_ms=500, success=True),
        )
        mock_client.generate = AsyncMock(return_value=mock_result)

        rewriter = SPRewriterAI(ollama_client=mock_client)
        result, attempt = await rewriter.rewrite(
            sp_name="sp_Test",
            sp_definition="CREATE PROCEDURE sp_Test AS SELECT 1",
            classification=SPClassification.MODERATE,
        )

        assert result.success is False
        assert "parse" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_rewrite_validation_failure(self):
        """Test handling SQL validation failure."""
        mock_client = MagicMock()
        mock_client.config = OllamaConfig(enabled=True)

        # Mock response with invalid SQL
        mock_result = OllamaResult(
            success=True,
            response="""
```sql
UPDATE customers SET name = 'test'
```

Confidence: high

Explanation: This is an update statement.
""",
            metrics=OllamaMetrics(request_time_ms=500, success=True),
        )
        mock_client.generate = AsyncMock(return_value=mock_result)

        rewriter = SPRewriterAI(ollama_client=mock_client)
        result, attempt = await rewriter.rewrite(
            sp_name="sp_Test",
            sp_definition="CREATE PROCEDURE sp_Test AS UPDATE customers SET name = 'test'",
            classification=SPClassification.MODERATE,
        )

        assert result.success is False
        assert "validation" in result.error_message.lower()
        assert attempt.is_valid is False

    @pytest.mark.asyncio
    async def test_rewrite_timeout(self):
        """Test handling timeout."""
        mock_client = MagicMock()
        mock_client.config = OllamaConfig(enabled=True)

        # Mock slow response that times out
        async def slow_generate(*args, **kwargs):
            await asyncio.sleep(10)  # Will be cancelled
            return OllamaResult(success=True, response="")

        mock_client.generate = slow_generate

        rewriter = SPRewriterAI(
            ollama_client=mock_client,
            timeout=0.1,  # Very short timeout
        )

        result, attempt = await rewriter.rewrite(
            sp_name="sp_Test",
            sp_definition="CREATE PROCEDURE sp_Test AS SELECT 1",
            classification=SPClassification.MODERATE,
        )

        assert result.success is False
        assert "timed out" in result.error_message.lower()


class TestPromptTemplates:
    """Tests for prompt templates."""

    def test_system_prompt_content(self):
        """Test system prompt contains key elements."""
        assert "SQL Server" in SYSTEM_PROMPT
        assert "Snowflake" in SYSTEM_PROMPT
        assert "GETDATE" in SYSTEM_PROMPT
        assert "CURRENT_TIMESTAMP" in SYSTEM_PROMPT

    def test_user_prompt_template_placeholders(self):
        """Test user prompt template has placeholders."""
        assert "{sp_definition}" in USER_PROMPT_TEMPLATE
        assert "{database}" in USER_PROMPT_TEMPLATE
        assert "{schema}" in USER_PROMPT_TEMPLATE
        assert "{table_context}" in USER_PROMPT_TEMPLATE


class TestAIRewriteSPFunction:
    """Tests for ai_rewrite_sp convenience function."""

    @pytest.mark.asyncio
    async def test_convenience_function(self):
        """Test convenience function creates rewriter and calls it."""
        with patch("app.services.sp_rewriter_ai.get_ollama_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.config = OllamaConfig(enabled=False)
            mock_get_client.return_value = mock_client

            result, attempt = await ai_rewrite_sp(
                sp_name="sp_Test",
                sp_definition="CREATE PROCEDURE sp_Test AS SELECT 1",
                classification=SPClassification.SIMPLE,
                database="TEST_DB",
                schema="TEST_SCHEMA",
            )

            assert result.success is False


class TestSPRewriterIntegration:
    """Integration tests for SPRewriter with AI."""

    @pytest.mark.asyncio
    async def test_rewrite_with_ai_simple_sp(self):
        """Test that simple SPs don't use AI."""
        from app.services.sp_rewriter import SPRewriter

        rewriter = SPRewriter(enable_ai=True)

        # Simple SP should use rule-based, not AI
        result, attempt = await rewriter.rewrite_with_ai(
            sp_name="sp_Simple",
            sp_definition="""
CREATE PROCEDURE sp_Simple
AS
SELECT customer_id, customer_name
FROM customers
WHERE status = 'active'
""",
        )

        # Should succeed with rule-based (no AI attempt)
        assert attempt is None
        # Simple SPs should be handled by rule-based

    @pytest.mark.asyncio
    async def test_rewrite_with_ai_no_definition(self):
        """Test handling missing SP definition."""
        from app.services.sp_rewriter import SPRewriter

        rewriter = SPRewriter(enable_ai=True)

        result, attempt = await rewriter.rewrite_with_ai(
            sp_name="sp_Missing",
            sp_definition=None,
        )

        assert result.success is False
        assert attempt is None
        assert "not available" in result.error_message.lower()
