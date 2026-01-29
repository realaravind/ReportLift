"""AI-Powered Guidance Generator Service.

Generates human-readable guidance for TODO items using AI (Ollama)
with fallback to static templates.
"""

import hashlib
import logging
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.services.ollama_service import OllamaClient, OllamaConfig, OllamaResult, get_ollama_client

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Schemas
# =============================================================================


class GuidanceCategory(str, Enum):
    """Categories of guidance items."""

    STORED_PROCEDURE = "stored_procedure"
    EXPRESSION = "expression"
    VISUAL = "visual"
    SUBREPORT = "subreport"
    CUSTOM_CODE = "custom_code"


class TodoGuidance(BaseModel):
    """Structured guidance for a TODO item."""

    summary: str = Field(description="1-2 sentence overview")
    detailed_explanation: str = Field(description="Detailed explanation paragraph")
    suggested_steps: list[str] = Field(description="Numbered action steps")
    challenges: list[str] | None = Field(default=None, description="Potential challenges")
    references: list[str] | None = Field(default=None, description="Documentation references")
    dax_equivalent: str | None = Field(default=None, description="DAX code for expressions")
    power_bi_config: str | None = Field(default=None, description="Power BI configuration")
    generated_by: Literal["ai", "template"] = Field(description="Generation method")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    cached: bool = Field(default=False, description="Whether response was cached")


class TodoGuidanceResponse(BaseModel):
    """Response schema for guidance API."""

    todo_id: str = Field(description="TODO item identifier")
    todo_title: str = Field(description="TODO item title")
    category: str = Field(description="TODO category")
    guidance: TodoGuidance = Field(description="Generated guidance")


class GuidanceGenerationLog(BaseModel):
    """Structured log for guidance generation."""

    event: Literal["guidance_generation", "guidance_fallback"] = Field(description="Event type")
    todo_id: str | None = Field(default=None, description="TODO item ID")
    todo_type: str = Field(description="TODO category")
    method: Literal["ai", "template"] = Field(description="Generation method")
    duration_ms: int = Field(description="Generation duration")
    cached: bool = Field(default=False, description="Whether cached")
    success: bool = Field(description="Whether successful")
    reason: str | None = Field(default=None, description="Fallback reason if applicable")


# =============================================================================
# Prompt Templates
# =============================================================================

SP_GUIDANCE_PROMPT = """Analyze this SQL Server stored procedure and provide conversion guidance for a developer who needs to manually convert it to Snowflake.

Stored Procedure Name: {sp_name}

Stored Procedure Definition:
```sql
{sp_definition}
```

Complexity Factors Identified:
{complexity_factors}

Please provide guidance in the following format:

SUMMARY:
[1-2 sentence overview of what this SP does and why it's complex]

DETAILED EXPLANATION:
[Paragraph explaining the specific challenges in converting this SP]

SUGGESTED STEPS:
1. [First step]
2. [Second step]
3. [Continue with specific, actionable steps]

CHALLENGES TO WATCH FOR:
- [Challenge 1]
- [Challenge 2]

SNOWFLAKE REFERENCES:
- [Relevant documentation link or feature name]
"""

EXPRESSION_GUIDANCE_PROMPT = """Analyze this SSRS expression and provide guidance for converting it to Power BI.

Expression:
{expression}

Location: {location}
Context: {context}
Pattern Detected: {pattern}

Please provide guidance in the following format:

SUMMARY:
[What this expression does in plain language]

DAX EQUIVALENT:
[The DAX expression or measure that achieves the same result, or "Requires custom solution"]

POWER BI CONFIGURATION:
[What Power BI visual settings or configurations are needed]

IMPLEMENTATION STEPS:
1. [Step 1]
2. [Step 2]

CHALLENGES TO WATCH FOR:
- [Challenge 1]
"""

VISUAL_GUIDANCE_PROMPT = """Analyze this SSRS visual element and provide guidance for recreating it in Power BI.

Visual Type: {visual_type}
Visual Name: {visual_name}
Context: {context}

Please provide guidance in the following format:

SUMMARY:
[Brief overview of the visual and conversion approach]

DETAILED EXPLANATION:
[Explanation of differences between SSRS and Power BI for this visual type]

SUGGESTED STEPS:
1. [Step 1]
2. [Step 2]

POWER BI CONFIGURATION:
[Specific Power BI settings and configurations needed]

CHALLENGES TO WATCH FOR:
- [Challenge 1]
"""

CUSTOM_CODE_GUIDANCE_PROMPT = """Analyze this custom VB.NET code from an SSRS report and provide guidance for converting it to DAX in Power BI.

Function Name: {function_name}
Parameters: {parameters}

Code:
```vb
{code}
```

Patterns Detected: {patterns}

Please provide guidance in the following format:

SUMMARY:
[What this function does and why it needs manual conversion]

DAX EQUIVALENT:
[The DAX measure or calculated column that achieves similar results]

IMPLEMENTATION STEPS:
1. [Step 1]
2. [Step 2]

CHALLENGES TO WATCH FOR:
- [Challenge 1]
"""


# =============================================================================
# Response Parser
# =============================================================================


class GuidanceResponseParser:
    """Parses AI-generated guidance into structured format."""

    # Patterns to extract sections
    SUMMARY_PATTERN = re.compile(
        r"SUMMARY:\s*\n?(.*?)(?=\n(?:DETAILED|DAX|IMPLEMENTATION|SUGGESTED|CHALLENGES|POWER BI|SNOWFLAKE)|$)",
        re.IGNORECASE | re.DOTALL,
    )
    DETAILED_PATTERN = re.compile(
        r"DETAILED EXPLANATION:\s*\n?(.*?)(?=\n(?:SUGGESTED|CHALLENGES|SNOWFLAKE|POWER BI)|$)",
        re.IGNORECASE | re.DOTALL,
    )
    STEPS_PATTERN = re.compile(
        r"(?:SUGGESTED STEPS|IMPLEMENTATION STEPS):\s*\n?(.*?)(?=\n(?:CHALLENGES|SNOWFLAKE|POWER BI|DAX)|$)",
        re.IGNORECASE | re.DOTALL,
    )
    CHALLENGES_PATTERN = re.compile(
        r"CHALLENGES TO WATCH FOR:\s*\n?(.*?)(?=\n(?:SNOWFLAKE|POWER BI|REFERENCES)|$)",
        re.IGNORECASE | re.DOTALL,
    )
    REFERENCES_PATTERN = re.compile(
        r"(?:SNOWFLAKE REFERENCES|REFERENCES):\s*\n?(.*?)$",
        re.IGNORECASE | re.DOTALL,
    )
    DAX_PATTERN = re.compile(
        r"DAX EQUIVALENT:\s*\n?(.*?)(?=\n(?:POWER BI|IMPLEMENTATION|CHALLENGES)|$)",
        re.IGNORECASE | re.DOTALL,
    )
    POWER_BI_PATTERN = re.compile(
        r"POWER BI CONFIGURATION:\s*\n?(.*?)(?=\n(?:IMPLEMENTATION|CHALLENGES|SUGGESTED)|$)",
        re.IGNORECASE | re.DOTALL,
    )

    @classmethod
    def parse(cls, raw_response: str, category: GuidanceCategory) -> TodoGuidance | None:
        """Parse AI response into structured guidance.

        Args:
            raw_response: Raw AI-generated text
            category: The category to determine which fields to extract

        Returns:
            TodoGuidance if parsing successful, None otherwise
        """
        try:
            # Extract summary
            summary_match = cls.SUMMARY_PATTERN.search(raw_response)
            summary = summary_match.group(1).strip() if summary_match else ""

            # Extract detailed explanation (or use summary for expressions)
            detailed_match = cls.DETAILED_PATTERN.search(raw_response)
            detailed = detailed_match.group(1).strip() if detailed_match else ""
            if not detailed:
                detailed = summary  # Use summary if no detailed section

            # Extract steps
            steps_match = cls.STEPS_PATTERN.search(raw_response)
            steps_text = steps_match.group(1).strip() if steps_match else ""
            suggested_steps = cls._parse_numbered_list(steps_text)

            # Extract challenges
            challenges_match = cls.CHALLENGES_PATTERN.search(raw_response)
            challenges_text = challenges_match.group(1).strip() if challenges_match else ""
            challenges = cls._parse_bullet_list(challenges_text) if challenges_text else None

            # Extract references
            references_match = cls.REFERENCES_PATTERN.search(raw_response)
            references_text = references_match.group(1).strip() if references_match else ""
            references = cls._parse_bullet_list(references_text) if references_text else None

            # Extract DAX equivalent (for expressions)
            dax_equivalent = None
            if category in (GuidanceCategory.EXPRESSION, GuidanceCategory.CUSTOM_CODE):
                dax_match = cls.DAX_PATTERN.search(raw_response)
                dax_equivalent = dax_match.group(1).strip() if dax_match else None

            # Extract Power BI config (for expressions and visuals)
            power_bi_config = None
            if category in (GuidanceCategory.EXPRESSION, GuidanceCategory.VISUAL, GuidanceCategory.CUSTOM_CODE):
                power_bi_match = cls.POWER_BI_PATTERN.search(raw_response)
                power_bi_config = power_bi_match.group(1).strip() if power_bi_match else None

            # Validate we got enough content
            if not summary or len(suggested_steps) == 0:
                logger.warning("Parsed guidance has missing required fields")
                return None

            return TodoGuidance(
                summary=summary,
                detailed_explanation=detailed or summary,
                suggested_steps=suggested_steps,
                challenges=challenges,
                references=references,
                dax_equivalent=dax_equivalent,
                power_bi_config=power_bi_config,
                generated_by="ai",
            )

        except Exception as e:
            logger.exception("Error parsing guidance response: %s", str(e))
            return None

    @classmethod
    def _parse_numbered_list(cls, text: str) -> list[str]:
        """Parse numbered list items from text."""
        items = []
        # Match patterns like "1. item" or "1) item" or "- item"
        pattern = re.compile(r"^\s*(?:\d+[\.\)]\s*|-\s*)(.*?)$", re.MULTILINE)
        for match in pattern.finditer(text):
            item = match.group(1).strip()
            if item:
                items.append(item)
        return items if items else [text.strip()] if text.strip() else []

    @classmethod
    def _parse_bullet_list(cls, text: str) -> list[str]:
        """Parse bullet list items from text."""
        items = []
        # Match patterns like "- item" or "* item" or "• item"
        pattern = re.compile(r"^\s*[-*•]\s*(.*?)$", re.MULTILINE)
        for match in pattern.finditer(text):
            item = match.group(1).strip()
            if item:
                items.append(item)
        return items if items else [text.strip()] if text.strip() else []


# =============================================================================
# Fallback Templates
# =============================================================================


def get_sp_fallback_template(
    sp_name: str | None = None,
    complexity: str | None = None,
) -> TodoGuidance:
    """Get fallback template for stored procedure guidance."""
    return TodoGuidance(
        summary=f"The stored procedure{' ' + sp_name if sp_name else ''} requires manual conversion to Snowflake SQL.",
        detailed_explanation=(
            "This stored procedure contains elements that cannot be automatically converted. "
            "Review the original SP definition and manually create equivalent Snowflake SQL queries. "
            f"Complexity level: {complexity or 'unknown'}."
        ),
        suggested_steps=[
            "Review the original stored procedure logic and document business requirements",
            "Identify input parameters and their data types",
            "Map SQL Server functions to Snowflake equivalents (e.g., GETDATE() -> CURRENT_TIMESTAMP())",
            "Convert temporary tables to Common Table Expressions (CTEs) or Snowflake temp tables",
            "Replace cursors with set-based operations",
            "Create the Snowflake SQL query matching the business logic",
            "Test the converted query with sample data",
            "Update the Power BI data source to use the new query",
        ],
        challenges=[
            "SQL Server-specific syntax may not have direct Snowflake equivalents",
            "Temporary tables need to be converted to CTEs or Snowflake temp tables",
            "Cursor-based logic needs to be rewritten as set-based operations",
            "Dynamic SQL may need restructuring",
            "Error handling syntax differs between platforms",
        ],
        references=[
            "Snowflake SQL Reference: https://docs.snowflake.com/en/sql-reference",
            "SQL Server to Snowflake Function Mapping Guide",
            "Snowflake Stored Procedures: https://docs.snowflake.com/en/sql-reference/stored-procedures",
        ],
        generated_by="template",
    )


def get_expression_fallback_template(
    expression: str | None = None,
    pattern: str | None = None,
    location: str | None = None,
) -> TodoGuidance:
    """Get fallback template for expression guidance."""
    return TodoGuidance(
        summary=f"This SSRS expression{' at ' + location if location else ''} requires manual conversion to DAX or Power BI measures.",
        detailed_explanation=(
            "The expression uses VB.NET syntax or functions that need to be rewritten using DAX "
            "(Data Analysis Expressions) in Power BI. "
            f"Pattern detected: {pattern or 'Complex expression'}."
        ),
        suggested_steps=[
            "Understand what the original expression calculates",
            "Identify the DAX function equivalents for each VB.NET function",
            "Create a new measure or calculated column in Power BI",
            "If referencing multiple fields, ensure proper table relationships",
            "Test the measure with the same data to verify results match",
            "Apply appropriate formatting",
        ],
        challenges=[
            "VB.NET procedural logic must be converted to DAX's functional style",
            "Some VB.NET functions may not have direct DAX equivalents",
            "Scope and context work differently in DAX",
            "Error handling requires IFERROR() wrapper",
        ],
        dax_equivalent="[Requires manual analysis - create appropriate DAX measure]",
        power_bi_config="Add as a measure to the appropriate table in Power BI model",
        generated_by="template",
    )


def get_visual_fallback_template(
    visual_type: str | None = None,
    visual_name: str | None = None,
) -> TodoGuidance:
    """Get fallback template for visual guidance."""
    return TodoGuidance(
        summary=f"The {visual_type or 'SSRS'} visual '{visual_name or 'element'}' requires manual recreation in Power BI.",
        detailed_explanation=(
            f"The SSRS visual type '{visual_type or 'unknown'}' does not have a direct equivalent in Power BI "
            "and needs to be manually recreated using available Power BI visuals or custom visuals from AppSource."
        ),
        suggested_steps=[
            "Review the original visual's purpose and data bindings",
            "Select an appropriate Power BI visual type or custom visual",
            "Configure the visual with equivalent data bindings",
            "Apply formatting to match the original appearance",
            "Test interactivity and filtering behavior",
        ],
        challenges=[
            "Some SSRS visual types have no direct Power BI equivalent",
            "Data bindings may need restructuring",
            "Pagination behavior differs between SSRS and Power BI",
        ],
        power_bi_config="Choose appropriate visual from Power BI gallery or AppSource",
        generated_by="template",
    )


def get_subreport_fallback_template(
    subreport_name: str | None = None,
    subreport_path: str | None = None,
) -> TodoGuidance:
    """Get fallback template for subreport guidance."""
    return TodoGuidance(
        summary=f"The subreport '{subreport_name or 'embedded report'}' must be converted separately.",
        detailed_explanation=(
            f"Subreports embedded in SSRS reports need to be converted independently. "
            f"Path: {subreport_path or 'embedded'}. "
            "In Power BI, subreports are typically replaced with drill-through pages, "
            "bookmarks, or separate report pages with navigation."
        ),
        suggested_steps=[
            "Locate and analyze the subreport RDL file",
            "Convert the subreport independently using this tool",
            "In Power BI, create a separate page for the subreport content",
            "Set up drill-through or bookmarks for navigation",
            "Configure parameters to pass as filters between pages",
            "Test the navigation flow matches the original SSRS behavior",
        ],
        challenges=[
            "Parameter passing works differently in Power BI",
            "Drill-through only works with specific visual interactions",
            "Exact layout replication may require paginated reports",
        ],
        power_bi_config="Create drill-through page or use bookmarks for navigation",
        generated_by="template",
    )


def get_custom_code_fallback_template(
    function_name: str | None = None,
    patterns: list[str] | None = None,
) -> TodoGuidance:
    """Get fallback template for custom VB code guidance."""
    patterns_str = ", ".join(patterns) if patterns else "various patterns"
    return TodoGuidance(
        summary=f"The VB function '{function_name or 'custom code'}' must be rewritten as DAX measures.",
        detailed_explanation=(
            f"Custom VB.NET code cannot be directly used in Power BI. "
            f"Detected patterns: {patterns_str}. "
            "The logic must be recreated using DAX measures or calculated columns."
        ),
        suggested_steps=[
            "Document what the original function calculates",
            "Identify the input parameters and their types",
            "Map VB.NET operations to DAX equivalents",
            "Create a new DAX measure with equivalent logic",
            "DAX does not support loops - restructure as calculations",
            "Test with known inputs/outputs from SSRS",
        ],
        challenges=[
            "DAX is purely functional - no procedural code",
            "Loops must be replaced with iterating functions (SUMX, FILTER, etc.)",
            "Global state/variables don't exist in DAX",
            "Error handling requires different approach",
        ],
        dax_equivalent="[Requires manual analysis - create appropriate DAX measure]",
        power_bi_config="Add as a measure to the appropriate table",
        generated_by="template",
    )


FALLBACK_TEMPLATES: dict[GuidanceCategory, Any] = {
    GuidanceCategory.STORED_PROCEDURE: get_sp_fallback_template,
    GuidanceCategory.EXPRESSION: get_expression_fallback_template,
    GuidanceCategory.VISUAL: get_visual_fallback_template,
    GuidanceCategory.SUBREPORT: get_subreport_fallback_template,
    GuidanceCategory.CUSTOM_CODE: get_custom_code_fallback_template,
}


# =============================================================================
# Guidance Cache
# =============================================================================


class GuidanceCache:
    """In-memory cache for guidance responses."""

    def __init__(self, ttl_seconds: int = 86400):  # 24 hours default
        """Initialize cache with TTL."""
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, tuple[TodoGuidance, datetime]] = {}

    def generate_key(self, category: str, content: str) -> str:
        """Generate cache key from category and content."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"guidance:{category}:{content_hash}"

    def get(self, key: str) -> TodoGuidance | None:
        """Get guidance from cache if not expired."""
        if key not in self._cache:
            return None

        guidance, cached_at = self._cache[key]
        elapsed = (datetime.now(timezone.utc) - cached_at).total_seconds()

        if elapsed > self.ttl_seconds:
            # Expired
            del self._cache[key]
            return None

        # Mark as cached
        guidance.cached = True
        return guidance

    def set(self, key: str, guidance: TodoGuidance) -> None:
        """Store guidance in cache."""
        self._cache[key] = (guidance, datetime.now(timezone.utc))

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    def cleanup_expired(self) -> int:
        """Remove expired entries and return count removed."""
        now = datetime.now(timezone.utc)
        expired_keys = [
            key
            for key, (_, cached_at) in self._cache.items()
            if (now - cached_at).total_seconds() > self.ttl_seconds
        ]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)


# =============================================================================
# Guidance Generator Service
# =============================================================================


class GuidanceGenerator:
    """Generates human-readable guidance for TODO items.

    Uses AI (Ollama) for intelligent guidance generation with
    automatic fallback to static templates when AI is unavailable.
    """

    def __init__(
        self,
        ollama_client: OllamaClient | None = None,
        cache_ttl_seconds: int = 86400,
    ):
        """Initialize the guidance generator.

        Args:
            ollama_client: Optional OllamaClient instance
            cache_ttl_seconds: Cache TTL in seconds (default 24 hours)
        """
        self._ollama_client = ollama_client
        self._cache = GuidanceCache(ttl_seconds=cache_ttl_seconds)

    def _get_ollama_client(self) -> OllamaClient:
        """Get or create Ollama client."""
        if self._ollama_client is None:
            self._ollama_client = get_ollama_client()
        return self._ollama_client

    async def generate_sp_guidance(
        self,
        sp_name: str,
        sp_definition: str | None = None,
        complexity: str | None = None,
        complexity_factors: list[str] | None = None,
        use_cache: bool = True,
    ) -> TodoGuidance:
        """Generate guidance for a stored procedure TODO.

        Args:
            sp_name: Name of the stored procedure
            sp_definition: Full SP definition (optional)
            complexity: Complexity level
            complexity_factors: List of identified complexity factors
            use_cache: Whether to use cached results

        Returns:
            TodoGuidance with AI-generated or template guidance
        """
        import time

        start_time = time.time()
        category = GuidanceCategory.STORED_PROCEDURE

        # Check cache
        cache_content = f"{sp_name}:{sp_definition or ''}"
        cache_key = self._cache.generate_key(category.value, cache_content)

        if use_cache:
            cached = self._cache.get(cache_key)
            if cached:
                logger.info(
                    "Using cached guidance for SP: %s",
                    sp_name,
                    extra={"event": "guidance_cache_hit", "sp_name": sp_name},
                )
                return cached

        # Try AI generation
        if sp_definition:
            try:
                client = self._get_ollama_client()
                if await client.is_available():
                    prompt = SP_GUIDANCE_PROMPT.format(
                        sp_name=sp_name,
                        sp_definition=sp_definition[:4000],  # Limit size
                        complexity_factors="\n".join(f"- {f}" for f in (complexity_factors or ["Complex logic"])),
                    )

                    result = await client.generate(prompt, temperature=0.3, max_tokens=1024)
                    duration_ms = int((time.time() - start_time) * 1000)

                    if result.success and result.response:
                        guidance = GuidanceResponseParser.parse(result.response, category)
                        if guidance:
                            # Cache and return
                            self._cache.set(cache_key, guidance)
                            self._log_generation(
                                event="guidance_generation",
                                todo_type=category.value,
                                method="ai",
                                duration_ms=duration_ms,
                                success=True,
                            )
                            return guidance

                    # AI failed, log and fallback
                    self._log_generation(
                        event="guidance_fallback",
                        todo_type=category.value,
                        method="template",
                        duration_ms=duration_ms,
                        success=False,
                        reason=result.error_message or "Parse failed",
                    )

            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                logger.exception("Error generating AI guidance for SP: %s", str(e))
                self._log_generation(
                    event="guidance_fallback",
                    todo_type=category.value,
                    method="template",
                    duration_ms=duration_ms,
                    success=False,
                    reason=str(e),
                )

        # Fallback to template
        duration_ms = int((time.time() - start_time) * 1000)
        guidance = get_sp_fallback_template(sp_name, complexity)
        self._cache.set(cache_key, guidance)
        return guidance

    async def generate_expression_guidance(
        self,
        expression: str,
        location: str | None = None,
        context: str | None = None,
        pattern: str | None = None,
        use_cache: bool = True,
    ) -> TodoGuidance:
        """Generate guidance for an expression TODO.

        Args:
            expression: The SSRS expression
            location: Where the expression is used
            context: Additional context
            pattern: Detected expression pattern
            use_cache: Whether to use cached results

        Returns:
            TodoGuidance with AI-generated or template guidance
        """
        import time

        start_time = time.time()
        category = GuidanceCategory.EXPRESSION

        # Check cache
        cache_content = f"{expression}:{location or ''}:{pattern or ''}"
        cache_key = self._cache.generate_key(category.value, cache_content)

        if use_cache:
            cached = self._cache.get(cache_key)
            if cached:
                return cached

        # Try AI generation
        try:
            client = self._get_ollama_client()
            if await client.is_available():
                prompt = EXPRESSION_GUIDANCE_PROMPT.format(
                    expression=expression[:2000],
                    location=location or "Report expression",
                    context=context or "SSRS report",
                    pattern=pattern or "Unknown",
                )

                result = await client.generate(prompt, temperature=0.3, max_tokens=1024)
                duration_ms = int((time.time() - start_time) * 1000)

                if result.success and result.response:
                    guidance = GuidanceResponseParser.parse(result.response, category)
                    if guidance:
                        self._cache.set(cache_key, guidance)
                        self._log_generation(
                            event="guidance_generation",
                            todo_type=category.value,
                            method="ai",
                            duration_ms=duration_ms,
                            success=True,
                        )
                        return guidance

                self._log_generation(
                    event="guidance_fallback",
                    todo_type=category.value,
                    method="template",
                    duration_ms=duration_ms,
                    success=False,
                    reason=result.error_message or "Parse failed",
                )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.exception("Error generating AI guidance for expression: %s", str(e))
            self._log_generation(
                event="guidance_fallback",
                todo_type=category.value,
                method="template",
                duration_ms=duration_ms,
                success=False,
                reason=str(e),
            )

        # Fallback to template
        guidance = get_expression_fallback_template(expression, pattern, location)
        self._cache.set(cache_key, guidance)
        return guidance

    async def generate_visual_guidance(
        self,
        visual_type: str,
        visual_name: str,
        context: str | None = None,
        use_cache: bool = True,
    ) -> TodoGuidance:
        """Generate guidance for a visual TODO.

        Args:
            visual_type: Type of the visual (Map, Gauge, etc.)
            visual_name: Name of the visual
            context: Additional context
            use_cache: Whether to use cached results

        Returns:
            TodoGuidance with AI-generated or template guidance
        """
        import time

        start_time = time.time()
        category = GuidanceCategory.VISUAL

        # Check cache
        cache_content = f"{visual_type}:{visual_name}"
        cache_key = self._cache.generate_key(category.value, cache_content)

        if use_cache:
            cached = self._cache.get(cache_key)
            if cached:
                return cached

        # Try AI generation
        try:
            client = self._get_ollama_client()
            if await client.is_available():
                prompt = VISUAL_GUIDANCE_PROMPT.format(
                    visual_type=visual_type,
                    visual_name=visual_name,
                    context=context or "SSRS report visualization",
                )

                result = await client.generate(prompt, temperature=0.3, max_tokens=1024)
                duration_ms = int((time.time() - start_time) * 1000)

                if result.success and result.response:
                    guidance = GuidanceResponseParser.parse(result.response, category)
                    if guidance:
                        self._cache.set(cache_key, guidance)
                        self._log_generation(
                            event="guidance_generation",
                            todo_type=category.value,
                            method="ai",
                            duration_ms=duration_ms,
                            success=True,
                        )
                        return guidance

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.exception("Error generating AI guidance for visual: %s", str(e))

        # Fallback to template
        guidance = get_visual_fallback_template(visual_type, visual_name)
        self._cache.set(cache_key, guidance)
        return guidance

    async def generate_custom_code_guidance(
        self,
        function_name: str,
        code: str | None = None,
        parameters: list[str] | None = None,
        patterns: list[str] | None = None,
        use_cache: bool = True,
    ) -> TodoGuidance:
        """Generate guidance for custom VB code TODO.

        Args:
            function_name: Name of the VB function
            code: The VB code
            parameters: Function parameters
            patterns: Detected code patterns
            use_cache: Whether to use cached results

        Returns:
            TodoGuidance with AI-generated or template guidance
        """
        import time

        start_time = time.time()
        category = GuidanceCategory.CUSTOM_CODE

        # Check cache
        cache_content = f"{function_name}:{code or ''}"
        cache_key = self._cache.generate_key(category.value, cache_content)

        if use_cache:
            cached = self._cache.get(cache_key)
            if cached:
                return cached

        # Try AI generation
        if code:
            try:
                client = self._get_ollama_client()
                if await client.is_available():
                    prompt = CUSTOM_CODE_GUIDANCE_PROMPT.format(
                        function_name=function_name,
                        parameters=", ".join(parameters) if parameters else "None",
                        code=code[:2000],
                        patterns=", ".join(patterns) if patterns else "None detected",
                    )

                    result = await client.generate(prompt, temperature=0.3, max_tokens=1024)
                    duration_ms = int((time.time() - start_time) * 1000)

                    if result.success and result.response:
                        guidance = GuidanceResponseParser.parse(result.response, category)
                        if guidance:
                            self._cache.set(cache_key, guidance)
                            self._log_generation(
                                event="guidance_generation",
                                todo_type=category.value,
                                method="ai",
                                duration_ms=duration_ms,
                                success=True,
                            )
                            return guidance

            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                logger.exception("Error generating AI guidance for custom code: %s", str(e))

        # Fallback to template
        guidance = get_custom_code_fallback_template(function_name, patterns)
        self._cache.set(cache_key, guidance)
        return guidance

    async def generate_subreport_guidance(
        self,
        subreport_name: str,
        subreport_path: str | None = None,
        use_cache: bool = True,
    ) -> TodoGuidance:
        """Generate guidance for a subreport TODO.

        Args:
            subreport_name: Name of the subreport
            subreport_path: Path to the subreport
            use_cache: Whether to use cached results

        Returns:
            TodoGuidance (always uses template for subreports)
        """
        category = GuidanceCategory.SUBREPORT

        # Check cache
        cache_content = f"{subreport_name}:{subreport_path or ''}"
        cache_key = self._cache.generate_key(category.value, cache_content)

        if use_cache:
            cached = self._cache.get(cache_key)
            if cached:
                return cached

        # Subreports always use template (AI doesn't add much value here)
        guidance = get_subreport_fallback_template(subreport_name, subreport_path)
        self._cache.set(cache_key, guidance)
        return guidance

    def _log_generation(
        self,
        event: str,
        todo_type: str,
        method: str,
        duration_ms: int,
        success: bool,
        reason: str | None = None,
    ) -> None:
        """Log guidance generation event."""
        log_data = GuidanceGenerationLog(
            event=event,  # type: ignore
            todo_type=todo_type,
            method=method,  # type: ignore
            duration_ms=duration_ms,
            success=success,
            reason=reason,
        )
        logger.info(
            "Guidance generation: %s",
            event,
            extra=log_data.model_dump(),
        )


# =============================================================================
# Singleton Instance
# =============================================================================


_guidance_generator: GuidanceGenerator | None = None


def get_guidance_generator() -> GuidanceGenerator:
    """Get or create the global guidance generator instance."""
    global _guidance_generator
    if _guidance_generator is None:
        _guidance_generator = GuidanceGenerator()
    return _guidance_generator
