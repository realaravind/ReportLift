"""Tests for the guidance generator service."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.guidance_generator import (
    GuidanceCategory,
    GuidanceCache,
    GuidanceGenerator,
    GuidanceResponseParser,
    TodoGuidance,
    TodoGuidanceResponse,
    get_expression_fallback_template,
    get_sp_fallback_template,
    get_visual_fallback_template,
    get_subreport_fallback_template,
    get_custom_code_fallback_template,
    get_guidance_generator,
)
from app.services.ollama_service import OllamaClient, OllamaResult


class TestGuidanceCategory:
    """Tests for GuidanceCategory enum."""

    def test_enum_values(self):
        """Test all enum values exist."""
        assert GuidanceCategory.STORED_PROCEDURE.value == "stored_procedure"
        assert GuidanceCategory.EXPRESSION.value == "expression"
        assert GuidanceCategory.VISUAL.value == "visual"
        assert GuidanceCategory.SUBREPORT.value == "subreport"
        assert GuidanceCategory.CUSTOM_CODE.value == "custom_code"


class TestTodoGuidance:
    """Tests for TodoGuidance schema."""

    def test_basic_creation(self):
        """Test creating basic guidance."""
        guidance = TodoGuidance(
            summary="Test summary",
            detailed_explanation="Test details",
            suggested_steps=["Step 1", "Step 2"],
            generated_by="ai",
        )
        assert guidance.summary == "Test summary"
        assert len(guidance.suggested_steps) == 2
        assert guidance.generated_by == "ai"
        assert guidance.generated_at is not None

    def test_full_guidance(self):
        """Test creating guidance with all fields."""
        guidance = TodoGuidance(
            summary="Full summary",
            detailed_explanation="Full details",
            suggested_steps=["Step 1", "Step 2", "Step 3"],
            challenges=["Challenge 1", "Challenge 2"],
            references=["Reference 1"],
            dax_equivalent="SUM(Table[Column])",
            power_bi_config="Add as measure",
            generated_by="template",
        )
        assert guidance.challenges is not None
        assert len(guidance.challenges) == 2
        assert guidance.dax_equivalent == "SUM(Table[Column])"


class TestGuidanceResponseParser:
    """Tests for GuidanceResponseParser."""

    def test_parse_sp_guidance(self):
        """Test parsing SP guidance response."""
        raw_response = """
SUMMARY:
This is a complex stored procedure that handles customer data.

DETAILED EXPLANATION:
The SP contains multiple temporary tables and cursor operations.

SUGGESTED STEPS:
1. Identify the main SELECT statement
2. Convert temp tables to CTEs
3. Replace cursor with set operations

CHALLENGES TO WATCH FOR:
- Dynamic SQL usage
- Complex cursor logic

SNOWFLAKE REFERENCES:
- Snowflake SQL Reference: https://docs.snowflake.com
"""
        guidance = GuidanceResponseParser.parse(raw_response, GuidanceCategory.STORED_PROCEDURE)

        assert guidance is not None
        assert "complex stored procedure" in guidance.summary
        assert len(guidance.suggested_steps) >= 3
        assert guidance.challenges is not None
        assert len(guidance.challenges) >= 1
        assert guidance.generated_by == "ai"

    def test_parse_expression_guidance(self):
        """Test parsing expression guidance response."""
        raw_response = """
SUMMARY:
This expression calculates a running total.

DAX EQUIVALENT:
CALCULATE(SUM(Sales[Amount]), FILTER(ALL(Sales), Sales[Date] <= MAX(Sales[Date])))

POWER BI CONFIGURATION:
Add as a measure to the Sales table.

IMPLEMENTATION STEPS:
1. Create a new measure
2. Copy the DAX expression

CHALLENGES TO WATCH FOR:
- Context transition
"""
        guidance = GuidanceResponseParser.parse(raw_response, GuidanceCategory.EXPRESSION)

        assert guidance is not None
        assert "running total" in guidance.summary
        assert guidance.dax_equivalent is not None
        assert "CALCULATE" in guidance.dax_equivalent
        assert guidance.power_bi_config is not None

    def test_parse_incomplete_response_returns_none(self):
        """Test parsing incomplete response returns None."""
        raw_response = "This is not properly formatted response."
        guidance = GuidanceResponseParser.parse(raw_response, GuidanceCategory.STORED_PROCEDURE)
        assert guidance is None

    def test_parse_numbered_list(self):
        """Test parsing numbered list items."""
        text = """
1. First step
2. Second step
3. Third step
"""
        items = GuidanceResponseParser._parse_numbered_list(text)
        assert len(items) == 3
        assert items[0] == "First step"

    def test_parse_bullet_list(self):
        """Test parsing bullet list items."""
        text = """
- Item one
- Item two
* Item three
"""
        items = GuidanceResponseParser._parse_bullet_list(text)
        assert len(items) == 3


class TestFallbackTemplates:
    """Tests for fallback template functions."""

    def test_sp_fallback_template(self):
        """Test SP fallback template."""
        guidance = get_sp_fallback_template("sp_GetCustomers", "complex")
        assert guidance.summary is not None
        assert "sp_GetCustomers" in guidance.summary
        assert len(guidance.suggested_steps) > 0
        assert guidance.generated_by == "template"
        assert guidance.challenges is not None

    def test_expression_fallback_template(self):
        """Test expression fallback template."""
        guidance = get_expression_fallback_template(
            expression="=IIf(Fields!Amount.Value > 100, 'High', 'Low')",
            pattern="iif",
            location="TextBox1",
        )
        assert "TextBox1" in guidance.summary
        assert guidance.dax_equivalent is not None
        assert guidance.generated_by == "template"

    def test_visual_fallback_template(self):
        """Test visual fallback template."""
        guidance = get_visual_fallback_template("Map", "RegionalSales")
        assert "Map" in guidance.summary
        assert "RegionalSales" in guidance.summary
        assert len(guidance.suggested_steps) > 0

    def test_subreport_fallback_template(self):
        """Test subreport fallback template."""
        guidance = get_subreport_fallback_template("CustomerDetails", "/Reports/CustomerDetails")
        assert "CustomerDetails" in guidance.summary
        assert len(guidance.suggested_steps) > 0
        assert guidance.power_bi_config is not None

    def test_custom_code_fallback_template(self):
        """Test custom code fallback template."""
        guidance = get_custom_code_fallback_template(
            function_name="FormatDate",
            patterns=["date_formatting", "string_manipulation"],
        )
        assert "FormatDate" in guidance.summary
        assert "date_formatting, string_manipulation" in guidance.detailed_explanation
        assert guidance.dax_equivalent is not None


class TestGuidanceCache:
    """Tests for GuidanceCache."""

    def test_cache_set_and_get(self):
        """Test setting and getting from cache."""
        cache = GuidanceCache(ttl_seconds=3600)
        guidance = TodoGuidance(
            summary="Test",
            detailed_explanation="Details",
            suggested_steps=["Step 1"],
            generated_by="ai",
        )

        cache_key = cache.generate_key("sp", "test_content")
        cache.set(cache_key, guidance)

        retrieved = cache.get(cache_key)
        assert retrieved is not None
        assert retrieved.summary == "Test"
        assert retrieved.cached is True

    def test_cache_miss(self):
        """Test cache miss returns None."""
        cache = GuidanceCache()
        result = cache.get("nonexistent_key")
        assert result is None

    def test_cache_expiry(self):
        """Test cache expiry."""
        from datetime import timedelta

        cache = GuidanceCache(ttl_seconds=60)  # 60 second expiry
        guidance = TodoGuidance(
            summary="Test",
            detailed_explanation="Details",
            suggested_steps=["Step 1"],
            generated_by="ai",
        )

        cache_key = cache.generate_key("sp", "test_content")
        cache.set(cache_key, guidance)

        # Should be available immediately
        result = cache.get(cache_key)
        assert result is not None

        # Manually expire by setting cache time to past
        old_time = datetime.now(timezone.utc) - timedelta(seconds=120)
        cache._cache[cache_key] = (guidance, old_time)

        # Should be expired now
        result = cache.get(cache_key)
        assert result is None

    def test_generate_key(self):
        """Test cache key generation."""
        cache = GuidanceCache()
        key1 = cache.generate_key("sp", "content1")
        key2 = cache.generate_key("sp", "content2")
        key3 = cache.generate_key("expression", "content1")

        assert key1 != key2  # Different content
        assert key1 != key3  # Different category
        assert key1.startswith("guidance:sp:")

    def test_clear_cache(self):
        """Test clearing cache."""
        cache = GuidanceCache()
        guidance = TodoGuidance(
            summary="Test",
            detailed_explanation="Details",
            suggested_steps=["Step 1"],
            generated_by="ai",
        )

        cache.set("key1", guidance)
        cache.set("key2", guidance)

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestGuidanceGenerator:
    """Tests for GuidanceGenerator service."""

    @pytest.fixture
    def mock_ollama_client(self):
        """Create a mock Ollama client."""
        client = MagicMock(spec=OllamaClient)
        client.is_available = AsyncMock(return_value=True)
        client.generate = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_generate_sp_guidance_with_ai(self, mock_ollama_client):
        """Test generating SP guidance with AI."""
        mock_ollama_client.generate.return_value = OllamaResult(
            success=True,
            response="""
SUMMARY:
Complex SP that needs conversion.

DETAILED EXPLANATION:
This SP has cursor operations.

SUGGESTED STEPS:
1. Remove cursors
2. Use CTEs

CHALLENGES TO WATCH FOR:
- Cursor complexity
""",
        )

        generator = GuidanceGenerator(ollama_client=mock_ollama_client)
        guidance = await generator.generate_sp_guidance(
            sp_name="sp_Test",
            sp_definition="CREATE PROCEDURE sp_Test AS ...",
            use_cache=False,
        )

        assert guidance is not None
        assert "Complex SP" in guidance.summary
        assert guidance.generated_by == "ai"
        mock_ollama_client.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_sp_guidance_fallback(self, mock_ollama_client):
        """Test SP guidance falls back to template when AI unavailable."""
        mock_ollama_client.is_available = AsyncMock(return_value=False)

        generator = GuidanceGenerator(ollama_client=mock_ollama_client)
        guidance = await generator.generate_sp_guidance(
            sp_name="sp_Test",
            sp_definition="CREATE PROCEDURE sp_Test AS ...",
            use_cache=False,
        )

        assert guidance is not None
        assert guidance.generated_by == "template"
        mock_ollama_client.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_sp_guidance_uses_cache(self, mock_ollama_client):
        """Test SP guidance uses cache."""
        mock_ollama_client.generate.return_value = OllamaResult(
            success=True,
            response="""
SUMMARY:
Test summary.

SUGGESTED STEPS:
1. Step 1
""",
        )

        generator = GuidanceGenerator(ollama_client=mock_ollama_client)

        # First call
        guidance1 = await generator.generate_sp_guidance(
            sp_name="sp_Test",
            sp_definition="CREATE PROCEDURE sp_Test AS ...",
            use_cache=True,
        )

        # Second call should use cache
        guidance2 = await generator.generate_sp_guidance(
            sp_name="sp_Test",
            sp_definition="CREATE PROCEDURE sp_Test AS ...",
            use_cache=True,
        )

        # Should only call AI once
        assert mock_ollama_client.generate.call_count == 1
        assert guidance2.cached is True

    @pytest.mark.asyncio
    async def test_generate_expression_guidance(self, mock_ollama_client):
        """Test generating expression guidance."""
        mock_ollama_client.is_available = AsyncMock(return_value=False)

        generator = GuidanceGenerator(ollama_client=mock_ollama_client)
        guidance = await generator.generate_expression_guidance(
            expression="=Sum(Fields!Amount.Value)",
            location="TextBox1",
            pattern="aggregate",
            use_cache=False,
        )

        assert guidance is not None
        assert guidance.generated_by == "template"
        assert guidance.dax_equivalent is not None

    @pytest.mark.asyncio
    async def test_generate_visual_guidance(self, mock_ollama_client):
        """Test generating visual guidance."""
        mock_ollama_client.is_available = AsyncMock(return_value=False)

        generator = GuidanceGenerator(ollama_client=mock_ollama_client)
        guidance = await generator.generate_visual_guidance(
            visual_type="Map",
            visual_name="RegionalSalesMap",
            use_cache=False,
        )

        assert guidance is not None
        assert "Map" in guidance.summary
        assert guidance.generated_by == "template"

    @pytest.mark.asyncio
    async def test_generate_subreport_guidance(self, mock_ollama_client):
        """Test generating subreport guidance always uses template."""
        generator = GuidanceGenerator(ollama_client=mock_ollama_client)
        guidance = await generator.generate_subreport_guidance(
            subreport_name="DetailReport",
            subreport_path="/Reports/Detail",
            use_cache=False,
        )

        assert guidance is not None
        assert guidance.generated_by == "template"
        # AI should not be called for subreports
        mock_ollama_client.is_available.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_custom_code_guidance(self, mock_ollama_client):
        """Test generating custom code guidance."""
        mock_ollama_client.is_available = AsyncMock(return_value=False)

        generator = GuidanceGenerator(ollama_client=mock_ollama_client)
        guidance = await generator.generate_custom_code_guidance(
            function_name="CalculateBonus",
            code="Public Function CalculateBonus(salary) ...",
            parameters=["salary"],
            patterns=["math_operations"],
            use_cache=False,
        )

        assert guidance is not None
        assert "CalculateBonus" in guidance.summary
        assert guidance.generated_by == "template"

    @pytest.mark.asyncio
    async def test_generate_sp_guidance_ai_error_fallback(self, mock_ollama_client):
        """Test SP guidance falls back on AI error."""
        mock_ollama_client.generate.side_effect = Exception("AI error")

        generator = GuidanceGenerator(ollama_client=mock_ollama_client)
        guidance = await generator.generate_sp_guidance(
            sp_name="sp_Test",
            sp_definition="CREATE PROCEDURE sp_Test AS ...",
            use_cache=False,
        )

        assert guidance is not None
        assert guidance.generated_by == "template"


class TestTodoGuidanceResponse:
    """Tests for TodoGuidanceResponse schema."""

    def test_response_creation(self):
        """Test creating response schema."""
        guidance = TodoGuidance(
            summary="Test",
            detailed_explanation="Details",
            suggested_steps=["Step 1"],
            generated_by="ai",
        )

        response = TodoGuidanceResponse(
            todo_id="123",
            todo_title="Convert SP",
            category="stored_procedure",
            guidance=guidance,
        )

        assert response.todo_id == "123"
        assert response.category == "stored_procedure"
        assert response.guidance.summary == "Test"


class TestGetGuidanceGenerator:
    """Tests for get_guidance_generator singleton."""

    def test_returns_singleton(self):
        """Test that function returns same instance."""
        gen1 = get_guidance_generator()
        gen2 = get_guidance_generator()
        assert gen1 is gen2

    def test_generator_is_functional(self):
        """Test that returned generator is functional."""
        generator = get_guidance_generator()
        assert generator is not None
        assert hasattr(generator, "generate_sp_guidance")
        assert hasattr(generator, "generate_expression_guidance")
