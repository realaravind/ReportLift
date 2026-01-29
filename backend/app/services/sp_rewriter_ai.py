"""AI-Assisted Stored Procedure Rewriter Service.

This service uses Ollama AI to analyze and rewrite complex stored procedures
that cannot be handled by rule-based conversion.
"""

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional

import sqlparse
from pydantic import BaseModel, Field

from app.services.ollama_service import (
    OllamaClient,
    OllamaConfig,
    OllamaErrorCode,
    OllamaResult,
    get_ollama_client,
)
from app.services.sp_rewriter import (
    SPClassification,
    ConfidenceLevel,
    SPParameter,
    SPRewriteResult,
    ComplexityElement,
)

logger = logging.getLogger(__name__)


# ============================================
# Pydantic Schemas for AI Results
# ============================================


class AIConfidenceLevel(str, Enum):
    """Confidence levels from AI response."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AIRewriteResponse(BaseModel):
    """Parsed response from AI SP rewrite."""

    sql_statement: str = Field(description="Extracted SQL SELECT statement")
    confidence: AIConfidenceLevel = Field(description="AI confidence in the conversion")
    explanation: str = Field(description="AI explanation of the conversion")


class AIRewriteAttempt(BaseModel):
    """Record of an AI rewrite attempt."""

    sp_name: str = Field(description="Name of the stored procedure")
    sp_definition: str = Field(description="Original SP definition")
    generated_sql: Optional[str] = Field(default=None, description="AI-generated SQL")
    confidence: Optional[AIConfidenceLevel] = Field(default=None, description="AI confidence")
    explanation: Optional[str] = Field(default=None, description="AI explanation")
    is_valid: bool = Field(default=False, description="Whether SQL passed validation")
    validation_error: Optional[str] = Field(default=None, description="Validation error if any")
    method: str = Field(default="ai", description="Rewrite method: ai or rule-based")
    ai_raw_response: Optional[str] = Field(default=None, description="Raw AI response for debugging")
    prompt_tokens: Optional[int] = Field(default=None, description="Tokens in prompt")
    completion_tokens: Optional[int] = Field(default=None, description="Tokens in completion")
    duration_ms: int = Field(default=0, description="Request duration in milliseconds")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SQLValidationResult(BaseModel):
    """Result of SQL syntax validation."""

    is_valid: bool = Field(description="Whether SQL is syntactically valid")
    error_message: Optional[str] = Field(default=None, description="Error message if invalid")
    is_select: bool = Field(default=False, description="Whether SQL is a SELECT statement")
    has_snowflake_functions: bool = Field(default=False, description="Whether Snowflake functions detected")


# ============================================
# Prompt Templates
# ============================================


SYSTEM_PROMPT = """You are an expert SQL developer specializing in database migrations from SQL Server to Snowflake.
Your task is to convert SQL Server stored procedures to Snowflake SELECT statements.

Key differences to handle:
- SQL Server GETDATE() -> Snowflake CURRENT_TIMESTAMP()
- SQL Server ISNULL() -> Snowflake COALESCE() or IFNULL()
- SQL Server TOP N -> Snowflake LIMIT N
- SQL Server DATEADD/DATEDIFF -> Snowflake DATEADD/DATEDIFF
- SQL Server CONVERT/CAST -> Snowflake CAST or TRY_CAST
- SQL Server CHARINDEX -> Snowflake POSITION
- SQL Server LEN -> Snowflake LENGTH
- SQL Server ISNUMERIC -> Use TRY_CAST with IS NOT NULL check
- @ parameters -> $ session variables

Always provide your response in this exact format:
1. The converted SQL in a code block
2. A confidence level on its own line
3. An explanation of the conversion

Do not include any additional commentary outside this format."""


USER_PROMPT_TEMPLATE = """Convert the following SQL Server stored procedure to a Snowflake SELECT statement.

**Original Stored Procedure:**
```sql
{sp_definition}
```

**Target Configuration:**
- Database: {database}
- Schema: {schema}

{table_context}

**Requirements:**
- Convert all SQL Server functions to Snowflake equivalents
- Replace @parameters with $variable references (e.g., @CustomerID becomes $customerid)
- Preserve the business logic exactly
- Handle NULL values appropriately
- Use Snowflake date/time functions

**Output Format (IMPORTANT - follow this exactly):**

```sql
-- Your converted SELECT statement here
```

Confidence: [high/medium/low]

Explanation: [Brief explanation of the conversion decisions made]"""


# ============================================
# Response Parser
# ============================================


class AIResponseParser:
    """Parser for extracting structured data from AI responses."""

    # Patterns for extracting components
    SQL_BLOCK_PATTERN = re.compile(
        r"```(?:sql)?\s*(.*?)```",
        re.IGNORECASE | re.DOTALL
    )

    CONFIDENCE_PATTERN = re.compile(
        r"Confidence:\s*(high|medium|low)",
        re.IGNORECASE
    )

    EXPLANATION_PATTERN = re.compile(
        r"Explanation:\s*(.*?)(?:$|```)",
        re.IGNORECASE | re.DOTALL
    )

    @classmethod
    def parse(cls, raw_response: str) -> Optional[AIRewriteResponse]:
        """Parse AI response into structured components.

        Args:
            raw_response: Raw text response from AI

        Returns:
            AIRewriteResponse or None if parsing fails
        """
        if not raw_response:
            return None

        # Extract SQL block
        sql_match = cls.SQL_BLOCK_PATTERN.search(raw_response)
        if not sql_match:
            # Try to find raw SQL without code block
            sql_statement = cls._extract_raw_sql(raw_response)
        else:
            sql_statement = sql_match.group(1).strip()

        if not sql_statement:
            logger.warning("Could not extract SQL from AI response")
            return None

        # Clean up the SQL
        sql_statement = cls._clean_sql(sql_statement)

        # Extract confidence
        confidence_match = cls.CONFIDENCE_PATTERN.search(raw_response)
        if confidence_match:
            confidence_str = confidence_match.group(1).lower()
            confidence = AIConfidenceLevel(confidence_str)
        else:
            # Default to medium if not specified
            confidence = AIConfidenceLevel.MEDIUM

        # Extract explanation
        explanation_match = cls.EXPLANATION_PATTERN.search(raw_response)
        if explanation_match:
            explanation = explanation_match.group(1).strip()
        else:
            # Try to extract any text after the SQL block
            explanation = cls._extract_explanation_fallback(raw_response, sql_statement)

        return AIRewriteResponse(
            sql_statement=sql_statement,
            confidence=confidence,
            explanation=explanation,
        )

    @classmethod
    def _extract_raw_sql(cls, text: str) -> Optional[str]:
        """Try to extract SQL without code blocks."""
        # Look for SELECT statement
        select_match = re.search(
            r"(SELECT\s+.*?)(?:Confidence:|Explanation:|$)",
            text,
            re.IGNORECASE | re.DOTALL
        )
        if select_match:
            return select_match.group(1).strip()
        return None

    @classmethod
    def _clean_sql(cls, sql: str) -> str:
        """Clean up extracted SQL."""
        # Remove leading/trailing whitespace and comments
        sql = sql.strip()

        # Remove any markdown artifacts
        sql = re.sub(r"^--\s*sql\s*$", "", sql, flags=re.IGNORECASE | re.MULTILINE)

        # Ensure it ends with semicolon
        if sql and not sql.rstrip().endswith(";"):
            sql = sql.rstrip() + ";"

        return sql

    @classmethod
    def _extract_explanation_fallback(cls, text: str, sql: str) -> str:
        """Extract explanation as fallback when pattern doesn't match."""
        # Remove the SQL and try to find any remaining explanation
        remaining = text.replace(sql, "").strip()
        remaining = re.sub(r"```.*?```", "", remaining, flags=re.DOTALL)
        remaining = re.sub(r"Confidence:\s*\w+", "", remaining, flags=re.IGNORECASE)

        # Clean up
        remaining = remaining.strip()
        if len(remaining) > 500:
            remaining = remaining[:500] + "..."

        return remaining or "No explanation provided by AI"


# ============================================
# SQL Validator
# ============================================


class SQLValidator:
    """Validator for generated SQL statements."""

    # Snowflake-specific functions to detect
    SNOWFLAKE_FUNCTIONS = [
        "CURRENT_TIMESTAMP",
        "CURRENT_DATE",
        "CURRENT_TIME",
        "DATEADD",
        "DATEDIFF",
        "DATE_PART",
        "DATE_TRUNC",
        "TO_DATE",
        "TO_TIMESTAMP",
        "TO_VARCHAR",
        "TO_NUMBER",
        "COALESCE",
        "IFNULL",
        "IFF",
        "TRY_CAST",
        "TRY_TO_DATE",
        "TRY_TO_NUMBER",
        "LENGTH",
        "POSITION",
        "SPLIT_PART",
        "ARRAY_AGG",
        "LISTAGG",
        "QUALIFY",
        "FLATTEN",
    ]

    # SQL Server functions that should be converted
    SQL_SERVER_FUNCTIONS = [
        "GETDATE",
        "ISNULL",
        "CHARINDEX",
        "LEN",
        "ISNUMERIC",
        "CONVERT",
        "DATEPART",
        "STUFF",
        "PATINDEX",
    ]

    @classmethod
    def validate(cls, sql: str) -> SQLValidationResult:
        """Validate SQL statement.

        Args:
            sql: SQL statement to validate

        Returns:
            SQLValidationResult with validation status
        """
        if not sql or not sql.strip():
            return SQLValidationResult(
                is_valid=False,
                error_message="Empty SQL statement",
            )

        try:
            # Parse with sqlparse
            parsed = sqlparse.parse(sql)

            if not parsed:
                return SQLValidationResult(
                    is_valid=False,
                    error_message="Failed to parse SQL statement",
                )

            # Check if it's a SELECT statement
            stmt = parsed[0]
            stmt_type = stmt.get_type()

            is_select = stmt_type == "SELECT"
            if not is_select:
                return SQLValidationResult(
                    is_valid=False,
                    error_message=f"Expected SELECT statement, got {stmt_type or 'unknown'}",
                    is_select=False,
                )

            # Check for Snowflake functions
            has_snowflake_functions = cls._check_snowflake_functions(sql)

            # Check for remaining SQL Server functions (warning, not error)
            sql_server_issues = cls._check_sql_server_functions(sql)
            if sql_server_issues:
                logger.warning(
                    "SQL may contain unconverted SQL Server functions: %s",
                    sql_server_issues
                )

            # Check for basic syntax issues
            syntax_issues = cls._check_basic_syntax(sql)
            if syntax_issues:
                return SQLValidationResult(
                    is_valid=False,
                    error_message=syntax_issues,
                    is_select=True,
                )

            return SQLValidationResult(
                is_valid=True,
                is_select=True,
                has_snowflake_functions=has_snowflake_functions,
            )

        except Exception as e:
            logger.exception("SQL validation error: %s", str(e))
            return SQLValidationResult(
                is_valid=False,
                error_message=f"Validation error: {str(e)}",
            )

    @classmethod
    def _check_snowflake_functions(cls, sql: str) -> bool:
        """Check if SQL contains Snowflake-specific functions."""
        sql_upper = sql.upper()
        return any(func in sql_upper for func in cls.SNOWFLAKE_FUNCTIONS)

    @classmethod
    def _check_sql_server_functions(cls, sql: str) -> list[str]:
        """Check for SQL Server functions that should have been converted."""
        sql_upper = sql.upper()
        issues = []
        for func in cls.SQL_SERVER_FUNCTIONS:
            # Check for function call pattern (function followed by open paren)
            if re.search(rf"\b{func}\s*\(", sql_upper):
                issues.append(func)
        return issues

    @classmethod
    def _check_basic_syntax(cls, sql: str) -> Optional[str]:
        """Check for basic syntax issues."""
        # Check balanced parentheses
        open_count = sql.count("(")
        close_count = sql.count(")")
        if open_count != close_count:
            return f"Unbalanced parentheses: {open_count} open, {close_count} close"

        # Check balanced quotes
        single_quotes = sql.count("'") - sql.count("\\'") - sql.count("''")
        if single_quotes % 2 != 0:
            return "Unbalanced single quotes"

        # Check for SELECT keyword
        if not re.search(r"\bSELECT\b", sql, re.IGNORECASE):
            return "Missing SELECT keyword"

        return None


# ============================================
# AI SP Rewriter Service
# ============================================


class SPRewriterAI:
    """AI-assisted stored procedure rewriter."""

    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        database: Optional[str] = None,
        schema: Optional[str] = None,
        timeout: int = 60,
    ):
        """Initialize the AI rewriter.

        Args:
            ollama_client: OllamaClient instance (uses global if None)
            database: Target Snowflake database
            schema: Target Snowflake schema
            timeout: Request timeout in seconds
        """
        self.ollama_client = ollama_client
        self.database = database or "{DATABASE}"
        self.schema = schema or "{SCHEMA}"
        self.timeout = timeout

    def _get_client(self) -> OllamaClient:
        """Get the Ollama client."""
        if self.ollama_client is None:
            return get_ollama_client()
        return self.ollama_client

    async def rewrite(
        self,
        sp_name: str,
        sp_definition: str,
        classification: SPClassification,
        parameters: Optional[list[SPParameter]] = None,
        table_context: Optional[str] = None,
    ) -> tuple[SPRewriteResult, AIRewriteAttempt]:
        """Attempt to rewrite SP using AI.

        Args:
            sp_name: Name of the stored procedure
            sp_definition: Full SP definition
            classification: SP classification
            parameters: Extracted SP parameters
            table_context: Optional context about available tables

        Returns:
            Tuple of (SPRewriteResult, AIRewriteAttempt)
        """
        start_time = time.time()
        attempt = AIRewriteAttempt(
            sp_name=sp_name,
            sp_definition=sp_definition,
        )

        client = self._get_client()

        # Check if AI is available
        if not client.config.enabled:
            return self._create_fallback_result(
                sp_name=sp_name,
                classification=classification,
                parameters=parameters or [],
                error_message="Ollama AI is not enabled",
            ), attempt

        # Build the prompt
        prompt = self._build_prompt(
            sp_definition=sp_definition,
            table_context=table_context,
        )

        # Make AI request
        try:
            result = await asyncio.wait_for(
                client.generate(
                    prompt=f"{SYSTEM_PROMPT}\n\n{prompt}",
                    temperature=0.2,
                    max_tokens=2048,
                ),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            attempt.duration_ms = duration_ms
            logger.warning(
                "AI SP rewrite timed out for %s after %dms",
                sp_name,
                duration_ms,
            )
            return self._create_fallback_result(
                sp_name=sp_name,
                classification=classification,
                parameters=parameters or [],
                error_message=f"AI request timed out after {self.timeout}s",
            ), attempt

        duration_ms = int((time.time() - start_time) * 1000)
        attempt.duration_ms = duration_ms

        # Handle AI errors
        if not result.success:
            attempt.ai_raw_response = result.error_message
            logger.warning(
                "AI SP rewrite failed for %s: %s",
                sp_name,
                result.error_message,
            )
            return self._create_fallback_result(
                sp_name=sp_name,
                classification=classification,
                parameters=parameters or [],
                error_message=result.error_message or "AI request failed",
            ), attempt

        # Store metrics
        if result.metrics:
            attempt.prompt_tokens = result.metrics.prompt_tokens
            attempt.completion_tokens = result.metrics.completion_tokens

        # Parse the response
        attempt.ai_raw_response = result.response
        parsed = AIResponseParser.parse(result.response or "")

        if not parsed:
            logger.warning(
                "Failed to parse AI response for %s",
                sp_name,
            )
            return self._create_fallback_result(
                sp_name=sp_name,
                classification=classification,
                parameters=parameters or [],
                error_message="Failed to parse AI response",
            ), attempt

        attempt.generated_sql = parsed.sql_statement
        attempt.confidence = parsed.confidence
        attempt.explanation = parsed.explanation

        # Validate the generated SQL
        validation = SQLValidator.validate(parsed.sql_statement)
        attempt.is_valid = validation.is_valid
        attempt.validation_error = validation.error_message

        if not validation.is_valid:
            logger.warning(
                "AI-generated SQL failed validation for %s: %s",
                sp_name,
                validation.error_message,
            )
            return self._create_validation_failure_result(
                sp_name=sp_name,
                classification=classification,
                parameters=parameters or [],
                generated_sql=parsed.sql_statement,
                ai_confidence=parsed.confidence,
                ai_explanation=parsed.explanation,
                validation_error=validation.error_message or "Unknown validation error",
            ), attempt

        # Success - create result
        logger.info(
            "AI SP rewrite succeeded for %s",
            sp_name,
            extra={
                "event": "ai_sp_rewrite",
                "sp_name": sp_name,
                "complexity": classification.value,
                "method": "ai",
                "confidence": parsed.confidence.value,
                "is_valid": True,
                "duration_ms": duration_ms,
                "prompt_tokens": attempt.prompt_tokens,
                "completion_tokens": attempt.completion_tokens,
            },
        )

        return self._create_success_result(
            sp_name=sp_name,
            classification=classification,
            parameters=parameters or [],
            generated_sql=parsed.sql_statement,
            ai_confidence=parsed.confidence,
            ai_explanation=parsed.explanation,
        ), attempt

    def _build_prompt(
        self,
        sp_definition: str,
        table_context: Optional[str] = None,
    ) -> str:
        """Build the AI prompt for SP conversion.

        Args:
            sp_definition: Full SP definition
            table_context: Optional table schema context

        Returns:
            Formatted prompt string
        """
        table_context_section = ""
        if table_context:
            table_context_section = f"""**Available Tables:**
```
{table_context}
```"""

        return USER_PROMPT_TEMPLATE.format(
            sp_definition=sp_definition,
            database=self.database,
            schema=self.schema,
            table_context=table_context_section,
        )

    def _create_success_result(
        self,
        sp_name: str,
        classification: SPClassification,
        parameters: list[SPParameter],
        generated_sql: str,
        ai_confidence: AIConfidenceLevel,
        ai_explanation: str,
    ) -> SPRewriteResult:
        """Create a successful rewrite result."""
        # Map AI confidence to our confidence level
        if ai_confidence == AIConfidenceLevel.HIGH:
            confidence = ConfidenceLevel.HIGH
        elif ai_confidence == AIConfidenceLevel.MEDIUM:
            confidence = ConfidenceLevel.MEDIUM
        else:
            confidence = ConfidenceLevel.LOW

        # Add AI metadata to the SQL
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        full_sql = f"""-- ============================================
-- ReportLift SP Conversion Script
-- Generated: {timestamp}
-- Original SP: {sp_name}
-- Classification: {classification.value}
-- Confidence: {confidence.value}
-- Method: AI-Generated (Review Recommended)
-- ============================================

-- AI Explanation: {ai_explanation}

-- Converted Query (AI-Generated)
{generated_sql}
"""

        return SPRewriteResult(
            success=True,
            original_sp_name=sp_name,
            classification=classification,
            confidence=confidence,
            converted_sql=full_sql,
            parameters=parameters,
            validation_suggestions=[
                "Review AI-generated SQL carefully before production use",
                "Compare row counts between original SP and converted query",
                "Test with edge case parameters",
                f"AI Confidence: {ai_confidence.value}",
            ],
        )

    def _create_fallback_result(
        self,
        sp_name: str,
        classification: SPClassification,
        parameters: list[SPParameter],
        error_message: str,
    ) -> SPRewriteResult:
        """Create a fallback result when AI fails."""
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        placeholder_sql = f"""-- ============================================
-- ReportLift SP Conversion Script
-- Generated: {timestamp}
-- Original SP: {sp_name}
-- Classification: {classification.value}
-- Confidence: N/A (Manual conversion required)
-- Method: AI Unavailable - Fallback
-- ============================================

-- AI Error: {error_message}
-- TODO: Manual conversion required for {sp_name}

-- Placeholder query (replace with converted logic):
SELECT 'TODO: Implement converted query for {sp_name}' AS status;
"""

        return SPRewriteResult(
            success=False,
            original_sp_name=sp_name,
            classification=classification,
            confidence=ConfidenceLevel.NA,
            converted_sql=placeholder_sql,
            parameters=parameters,
            error_message=error_message,
            validation_suggestions=[
                "Full manual conversion required",
                "AI assistance was unavailable",
                "Review original SP logic carefully",
            ],
        )

    def _create_validation_failure_result(
        self,
        sp_name: str,
        classification: SPClassification,
        parameters: list[SPParameter],
        generated_sql: str,
        ai_confidence: AIConfidenceLevel,
        ai_explanation: str,
        validation_error: str,
    ) -> SPRewriteResult:
        """Create a result when AI SQL fails validation."""
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        placeholder_sql = f"""-- ============================================
-- ReportLift SP Conversion Script
-- Generated: {timestamp}
-- Original SP: {sp_name}
-- Classification: {classification.value}
-- Confidence: N/A (AI output failed validation)
-- Method: AI-Generated (INVALID - requires manual review)
-- ============================================

-- AI Explanation: {ai_explanation}
-- AI Confidence: {ai_confidence.value}
-- Validation Error: {validation_error}

-- AI-Generated SQL (FAILED VALIDATION - DO NOT USE AS-IS):
/*
{generated_sql}
*/

-- TODO: Fix or manually rewrite the query above

-- Placeholder query:
SELECT 'TODO: Fix AI-generated query for {sp_name}' AS status;
"""

        return SPRewriteResult(
            success=False,
            original_sp_name=sp_name,
            classification=classification,
            confidence=ConfidenceLevel.NA,
            converted_sql=placeholder_sql,
            parameters=parameters,
            error_message=f"AI-generated SQL failed validation: {validation_error}",
            validation_suggestions=[
                "AI generated SQL but it failed validation",
                f"Validation error: {validation_error}",
                "Review the AI-generated SQL in the comments",
                "Fix syntax issues and revalidate",
            ],
        )


# ============================================
# Integration function for existing SPRewriter
# ============================================


async def ai_rewrite_sp(
    sp_name: str,
    sp_definition: str,
    classification: SPClassification,
    parameters: Optional[list[SPParameter]] = None,
    database: Optional[str] = None,
    schema: Optional[str] = None,
    timeout: int = 60,
) -> tuple[SPRewriteResult, AIRewriteAttempt]:
    """Convenience function for AI-assisted SP rewriting.

    Args:
        sp_name: Name of the stored procedure
        sp_definition: Full SP definition
        classification: SP classification
        parameters: Extracted SP parameters
        database: Target Snowflake database
        schema: Target Snowflake schema
        timeout: Request timeout in seconds

    Returns:
        Tuple of (SPRewriteResult, AIRewriteAttempt)
    """
    rewriter = SPRewriterAI(
        database=database,
        schema=schema,
        timeout=timeout,
    )
    return await rewriter.rewrite(
        sp_name=sp_name,
        sp_definition=sp_definition,
        classification=classification,
        parameters=parameters,
    )
