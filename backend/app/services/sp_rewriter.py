"""Stored Procedure Rewriter Service.

This service handles classification and rewriting of SQL Server stored procedures
to Snowflake-compatible queries.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, TYPE_CHECKING

import sqlparse
from sqlparse.sql import Statement, Token
from sqlparse.tokens import Keyword, DML

from app.services.sql_generator import SQLGenerator

if TYPE_CHECKING:
    from app.services.sp_rewriter_ai import SPRewriterAI, AIRewriteAttempt

logger = logging.getLogger(__name__)


class SPClassification(str, Enum):
    """Classification levels for stored procedures."""
    SIMPLE = "SIMPLE"
    MODERATE = "MODERATE"
    COMPLEX = "COMPLEX"


class ConfidenceLevel(str, Enum):
    """Confidence level for SP rewrites."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NA = "N/A"


@dataclass
class ComplexityElement:
    """Represents a detected complexity element in an SP."""
    element_type: str
    description: str
    line_hint: Optional[str] = None


@dataclass
class SPClassificationResult:
    """Result of SP classification."""
    classification: SPClassification
    complexity_elements: list[ComplexityElement] = field(default_factory=list)
    complexity_score: int = 0
    select_count: int = 0
    has_union: bool = False


@dataclass
class SPParameter:
    """Represents a stored procedure parameter."""
    name: str
    data_type: str
    direction: str = "IN"  # IN, OUT, INOUT
    default_value: Optional[str] = None


@dataclass
class SPRewriteResult:
    """Result of SP rewrite attempt."""
    success: bool
    original_sp_name: str
    classification: SPClassification
    confidence: ConfidenceLevel
    converted_sql: Optional[str] = None
    parameters: list[SPParameter] = field(default_factory=list)
    validation_suggestions: list[str] = field(default_factory=list)
    error_message: Optional[str] = None
    complexity_elements: list[ComplexityElement] = field(default_factory=list)


class SPParser:
    """Parser for detecting complexity elements in stored procedures."""

    # Patterns for detecting complexity elements
    TEMP_TABLE_PATTERN = re.compile(
        r"(?:#[\w]+|@[\w]+\s+TABLE\b)",
        re.IGNORECASE
    )

    CURSOR_PATTERNS = [
        re.compile(r"\bDECLARE\s+\w+\s+CURSOR\b", re.IGNORECASE),
        re.compile(r"\bOPEN\s+\w+\b", re.IGNORECASE),
        re.compile(r"\bFETCH\s+(?:NEXT\s+)?FROM\b", re.IGNORECASE),
        re.compile(r"\bCLOSE\s+\w+\b", re.IGNORECASE),
        re.compile(r"\bDEALLOCATE\s+\w+\b", re.IGNORECASE),
    ]

    DYNAMIC_SQL_PATTERNS = [
        re.compile(r"\bEXEC(?:UTE)?\s*\(", re.IGNORECASE),
        re.compile(r"\bsp_executesql\b", re.IGNORECASE),
    ]

    TRANSACTION_PATTERNS = [
        re.compile(r"\bBEGIN\s+TRAN(?:SACTION)?\b", re.IGNORECASE),
        re.compile(r"\bCOMMIT\s*(?:TRAN(?:SACTION)?)?\b", re.IGNORECASE),
        re.compile(r"\bROLLBACK\s*(?:TRAN(?:SACTION)?)?\b", re.IGNORECASE),
    ]

    CONTROL_FLOW_PATTERNS = [
        re.compile(r"\bWHILE\s+", re.IGNORECASE),
        re.compile(r"\bGOTO\s+", re.IGNORECASE),
        re.compile(r"\bBREAK\b", re.IGNORECASE),
        re.compile(r"\bCONTINUE\b", re.IGNORECASE),
    ]

    IF_ELSE_PATTERN = re.compile(r"\bIF\s+", re.IGNORECASE)
    UNION_PATTERN = re.compile(r"\bUNION\s+(?:ALL\s+)?", re.IGNORECASE)

    def __init__(self, sp_definition: str):
        """Initialize parser with SP definition.

        Args:
            sp_definition: The full stored procedure definition text
        """
        self.sp_definition = sp_definition
        self.parsed = sqlparse.parse(sp_definition)
        self._complexity_elements: list[ComplexityElement] = []

    def detect_temp_tables(self) -> list[ComplexityElement]:
        """Detect temp table usage (#temp, @table variables)."""
        elements = []
        matches = self.TEMP_TABLE_PATTERN.findall(self.sp_definition)
        for match in matches:
            elements.append(ComplexityElement(
                element_type="temp_table",
                description=f"Temp table: {match}",
                line_hint=match
            ))
        return elements

    def detect_cursors(self) -> list[ComplexityElement]:
        """Detect cursor usage."""
        elements = []
        for pattern in self.CURSOR_PATTERNS:
            if pattern.search(self.sp_definition):
                match = pattern.search(self.sp_definition)
                elements.append(ComplexityElement(
                    element_type="cursor",
                    description="Cursor operation detected",
                    line_hint=match.group(0) if match else None
                ))
        return elements

    def detect_dynamic_sql(self) -> list[ComplexityElement]:
        """Detect dynamic SQL (EXEC, sp_executesql)."""
        elements = []
        for pattern in self.DYNAMIC_SQL_PATTERNS:
            if pattern.search(self.sp_definition):
                match = pattern.search(self.sp_definition)
                elements.append(ComplexityElement(
                    element_type="dynamic_sql",
                    description="Dynamic SQL detected",
                    line_hint=match.group(0) if match else None
                ))
        return elements

    def detect_transactions(self) -> list[ComplexityElement]:
        """Detect transaction handling."""
        elements = []
        for pattern in self.TRANSACTION_PATTERNS:
            if pattern.search(self.sp_definition):
                match = pattern.search(self.sp_definition)
                elements.append(ComplexityElement(
                    element_type="transaction",
                    description="Transaction control detected",
                    line_hint=match.group(0) if match else None
                ))
        return elements

    def detect_control_flow(self) -> list[ComplexityElement]:
        """Detect control flow statements (WHILE, GOTO, etc.)."""
        elements = []
        for pattern in self.CONTROL_FLOW_PATTERNS:
            if pattern.search(self.sp_definition):
                match = pattern.search(self.sp_definition)
                elements.append(ComplexityElement(
                    element_type="control_flow",
                    description="Loop/control flow detected",
                    line_hint=match.group(0) if match else None
                ))
        return elements

    def count_if_else(self) -> int:
        """Count IF statements in the SP."""
        return len(self.IF_ELSE_PATTERN.findall(self.sp_definition))

    def count_select_statements(self) -> int:
        """Count SELECT statements in the SP."""
        count = 0
        for statement in self.parsed:
            tokens = list(statement.flatten())
            for token in tokens:
                if token.ttype is DML and token.value.upper() == "SELECT":
                    count += 1
        return count

    def has_union(self) -> bool:
        """Check if SP contains UNION or UNION ALL."""
        return bool(self.UNION_PATTERN.search(self.sp_definition))

    def get_all_complexity_elements(self) -> list[ComplexityElement]:
        """Get all detected complexity elements."""
        elements = []
        elements.extend(self.detect_temp_tables())
        elements.extend(self.detect_cursors())
        elements.extend(self.detect_dynamic_sql())
        elements.extend(self.detect_transactions())
        elements.extend(self.detect_control_flow())
        return elements


class SPClassifier:
    """Classifier for stored procedures."""

    def __init__(self, parser: SPParser):
        """Initialize classifier with parser.

        Args:
            parser: SPParser instance with parsed SP
        """
        self.parser = parser

    def classify(self) -> SPClassificationResult:
        """Classify the stored procedure.

        Returns:
            SPClassificationResult with classification and details
        """
        complexity_elements = self.parser.get_all_complexity_elements()
        select_count = self.parser.count_select_statements()
        has_union = self.parser.has_union()
        if_count = self.parser.count_if_else()

        # Calculate complexity score
        complexity_score = len(complexity_elements) * 10
        complexity_score += max(0, select_count - 1) * 2  # Multiple SELECTs add complexity
        complexity_score += if_count * 3  # IF statements add some complexity

        # Determine classification
        if complexity_elements:
            # Any complex element (temp tables, cursors, dynamic SQL, transactions, loops)
            classification = SPClassification.COMPLEX
        elif select_count <= 1 and if_count == 0 and not has_union:
            # Single SELECT, no IF, no UNION = SIMPLE
            classification = SPClassification.SIMPLE
        elif select_count > 1 or has_union or if_count <= 1:
            # Multiple SELECTs with UNION, or simple IF/ELSE = MODERATE
            classification = SPClassification.MODERATE
        else:
            # Default to COMPLEX for anything uncertain
            classification = SPClassification.COMPLEX

        return SPClassificationResult(
            classification=classification,
            complexity_elements=complexity_elements,
            complexity_score=complexity_score,
            select_count=select_count,
            has_union=has_union,
        )


class SPRewriter:
    """Main SP rewriter service."""

    def __init__(
        self,
        database: Optional[str] = None,
        schema: Optional[str] = None,
        warehouse: Optional[str] = None,
        enable_ai: bool = True,
    ):
        """Initialize rewriter.

        Args:
            database: Target Snowflake database
            schema: Target Snowflake schema
            warehouse: Target Snowflake warehouse
            enable_ai: Whether to use AI for complex SPs
        """
        self.database = database or "{DATABASE}"
        self.schema = schema or "{SCHEMA}"
        self.warehouse = warehouse or "{WAREHOUSE}"
        self.enable_ai = enable_ai
        self._ai_rewriter: Optional["SPRewriterAI"] = None
        self.sql_generator = SQLGenerator(
            database=self.database,
            schema=self.schema,
            warehouse=self.warehouse,
        )

    def _get_ai_rewriter(self) -> "SPRewriterAI":
        """Get or create the AI rewriter instance."""
        if self._ai_rewriter is None:
            from app.services.sp_rewriter_ai import SPRewriterAI
            self._ai_rewriter = SPRewriterAI(
                database=self.database,
                schema=self.schema,
            )
        return self._ai_rewriter

    def rewrite(
        self,
        sp_name: str,
        sp_definition: Optional[str] = None,
        sp_call: Optional[str] = None,
    ) -> SPRewriteResult:
        """Rewrite a stored procedure to Snowflake-compatible SQL.

        Args:
            sp_name: Name of the stored procedure
            sp_definition: Full SP definition (CREATE PROCEDURE ...)
            sp_call: The SP call syntax (EXEC sp_name @param1, @param2)

        Returns:
            SPRewriteResult with rewrite details
        """
        if not sp_definition:
            # No definition available - generate placeholder
            return self._generate_placeholder(
                sp_name=sp_name,
                sp_call=sp_call,
                reason="SP definition not available",
            )

        # Parse and classify
        parser = SPParser(sp_definition)
        classifier = SPClassifier(parser)
        classification_result = classifier.classify()

        # Route to appropriate handler
        if classification_result.classification == SPClassification.SIMPLE:
            return self._rewrite_simple(
                sp_name=sp_name,
                sp_definition=sp_definition,
                parser=parser,
                classification_result=classification_result,
            )
        elif classification_result.classification == SPClassification.MODERATE:
            return self._rewrite_moderate(
                sp_name=sp_name,
                sp_definition=sp_definition,
                parser=parser,
                classification_result=classification_result,
            )
        else:
            return self._handle_complex(
                sp_name=sp_name,
                sp_definition=sp_definition,
                classification_result=classification_result,
            )

    def _extract_sp_parameters(self, sp_definition: str) -> list[SPParameter]:
        """Extract parameters from SP definition.

        Args:
            sp_definition: Full SP definition

        Returns:
            List of SPParameter objects
        """
        parameters = []

        # Pattern to match parameter declarations
        # Matches: @ParamName DataType [= DefaultValue]
        param_pattern = re.compile(
            r"@(\w+)\s+(\w+(?:\([^)]+\))?)\s*(?:=\s*([^,\n]+))?",
            re.IGNORECASE
        )

        # Find the parameter section (between CREATE PROCEDURE ... AS)
        as_match = re.search(r"\bAS\b", sp_definition, re.IGNORECASE)
        if as_match:
            param_section = sp_definition[:as_match.start()]
        else:
            param_section = sp_definition

        for match in param_pattern.finditer(param_section):
            param_name = match.group(1)
            data_type = match.group(2)
            default_value = match.group(3).strip() if match.group(3) else None

            # Skip common table keywords that might match
            if data_type.upper() in ("TABLE", "AS", "BEGIN", "END"):
                continue

            parameters.append(SPParameter(
                name=param_name,
                data_type=data_type,
                default_value=default_value,
            ))

        return parameters

    def _extract_select_statement(self, sp_definition: str) -> Optional[str]:
        """Extract the main SELECT statement from SP body.

        Args:
            sp_definition: Full SP definition

        Returns:
            Extracted SELECT statement or None
        """
        # Find the body section (after AS or BEGIN)
        body_match = re.search(
            r"\bAS\b\s*(?:BEGIN\s*)?(.*?)(?:\bEND\b\s*$|$)",
            sp_definition,
            re.IGNORECASE | re.DOTALL
        )

        if not body_match:
            return None

        body = body_match.group(1).strip()

        # Remove SET NOCOUNT ON and similar statements
        body = re.sub(r"\bSET\s+NOCOUNT\s+ON\b[;]?\s*", "", body, flags=re.IGNORECASE)
        body = re.sub(r"\bSET\s+NOCOUNT\s+OFF\b[;]?\s*", "", body, flags=re.IGNORECASE)

        # Extract SELECT statement
        select_match = re.search(
            r"\bSELECT\b.*",
            body,
            re.IGNORECASE | re.DOTALL
        )

        if select_match:
            select_sql = select_match.group(0).strip()
            # Remove trailing END if present
            select_sql = re.sub(r"\s*\bEND\b\s*$", "", select_sql, flags=re.IGNORECASE)
            return select_sql

        return None

    def _rewrite_simple(
        self,
        sp_name: str,
        sp_definition: str,
        parser: SPParser,
        classification_result: SPClassificationResult,
    ) -> SPRewriteResult:
        """Rewrite a simple stored procedure.

        Args:
            sp_name: Name of the SP
            sp_definition: Full SP definition
            parser: SPParser instance
            classification_result: Classification result

        Returns:
            SPRewriteResult with converted SQL
        """
        parameters = self._extract_sp_parameters(sp_definition)
        select_sql = self._extract_select_statement(sp_definition)

        if not select_sql:
            return SPRewriteResult(
                success=False,
                original_sp_name=sp_name,
                classification=SPClassification.SIMPLE,
                confidence=ConfidenceLevel.NA,
                error_message="Could not extract SELECT statement from SP",
                parameters=parameters,
            )

        # Convert SQL using the SQL generator
        conversion_result = self.sql_generator.convert_sql(select_sql)
        converted_sql = conversion_result.converted_sql

        # Qualify table references
        converted_sql = self.sql_generator.qualify_table_references(converted_sql)

        # Convert parameters to Snowflake format
        param_declarations = self._generate_parameter_declarations(parameters)

        # Replace @param references with $param
        for param in parameters:
            pattern = re.compile(r"@" + re.escape(param.name) + r"\b", re.IGNORECASE)
            param_var = param.name.lower()
            converted_sql = pattern.sub(f"${param_var}", converted_sql)

        # Generate full script
        full_script = self._generate_script(
            sp_name=sp_name,
            classification=SPClassification.SIMPLE,
            confidence=ConfidenceLevel.HIGH,
            param_declarations=param_declarations,
            converted_sql=converted_sql,
            function_count=len(conversion_result.function_mappings),
        )

        return SPRewriteResult(
            success=True,
            original_sp_name=sp_name,
            classification=SPClassification.SIMPLE,
            confidence=ConfidenceLevel.HIGH,
            converted_sql=full_script,
            parameters=parameters,
            validation_suggestions=self._generate_validation_suggestions(
                ConfidenceLevel.HIGH
            ),
        )

    def _rewrite_moderate(
        self,
        sp_name: str,
        sp_definition: str,
        parser: SPParser,
        classification_result: SPClassificationResult,
    ) -> SPRewriteResult:
        """Attempt to rewrite a moderate stored procedure.

        Args:
            sp_name: Name of the SP
            sp_definition: Full SP definition
            parser: SPParser instance
            classification_result: Classification result

        Returns:
            SPRewriteResult with converted SQL or failure status
        """
        parameters = self._extract_sp_parameters(sp_definition)

        # Try to handle UNION queries
        if classification_result.has_union:
            select_sql = self._extract_select_statement(sp_definition)

            if select_sql:
                # Convert the combined UNION query
                conversion_result = self.sql_generator.convert_sql(select_sql)
                converted_sql = conversion_result.converted_sql
                converted_sql = self.sql_generator.qualify_table_references(converted_sql)

                # Replace @param references with $param
                for param in parameters:
                    pattern = re.compile(
                        r"@" + re.escape(param.name) + r"\b",
                        re.IGNORECASE
                    )
                    param_var = param.name.lower()
                    converted_sql = pattern.sub(f"${param_var}", converted_sql)

                param_declarations = self._generate_parameter_declarations(parameters)

                full_script = self._generate_script(
                    sp_name=sp_name,
                    classification=SPClassification.MODERATE,
                    confidence=ConfidenceLevel.MEDIUM,
                    param_declarations=param_declarations,
                    converted_sql=converted_sql,
                    function_count=len(conversion_result.function_mappings),
                )

                return SPRewriteResult(
                    success=True,
                    original_sp_name=sp_name,
                    classification=SPClassification.MODERATE,
                    confidence=ConfidenceLevel.MEDIUM,
                    converted_sql=full_script,
                    parameters=parameters,
                    validation_suggestions=self._generate_validation_suggestions(
                        ConfidenceLevel.MEDIUM
                    ),
                )

        # Try to handle simple IF/ELSE by extracting both branches
        if_count = parser.count_if_else()
        if if_count == 1:
            # Attempt to extract and combine IF/ELSE branches with CASE
            result = self._handle_simple_if_else(sp_name, sp_definition, parameters)
            if result.success:
                return result

        # If we can't handle it, return failure with LOW confidence placeholder
        return SPRewriteResult(
            success=False,
            original_sp_name=sp_name,
            classification=SPClassification.MODERATE,
            confidence=ConfidenceLevel.LOW,
            error_message="Unable to automatically rewrite moderate SP",
            parameters=parameters,
            converted_sql=self._generate_placeholder_script(
                sp_name=sp_name,
                sp_definition=sp_definition,
                classification=SPClassification.MODERATE,
                complexity_elements=[],
                reason="Moderate complexity - requires manual review",
            ),
            validation_suggestions=self._generate_validation_suggestions(
                ConfidenceLevel.LOW
            ),
        )

    def _handle_simple_if_else(
        self,
        sp_name: str,
        sp_definition: str,
        parameters: list[SPParameter],
    ) -> SPRewriteResult:
        """Attempt to handle simple IF/ELSE by converting to CASE.

        This is a simplified handler that works for basic IF/ELSE patterns.
        """
        # This is a simplified implementation - real-world IF/ELSE handling
        # would need more sophisticated parsing

        # For now, return failure - this can be enhanced later
        return SPRewriteResult(
            success=False,
            original_sp_name=sp_name,
            classification=SPClassification.MODERATE,
            confidence=ConfidenceLevel.LOW,
            error_message="IF/ELSE pattern too complex for auto-conversion",
            parameters=parameters,
        )

    def _handle_complex(
        self,
        sp_name: str,
        sp_definition: str,
        classification_result: SPClassificationResult,
    ) -> SPRewriteResult:
        """Handle a complex stored procedure (sync version).

        Args:
            sp_name: Name of the SP
            sp_definition: Full SP definition
            classification_result: Classification result

        Returns:
            SPRewriteResult with placeholder and TODO
        """
        placeholder_sql = self._generate_placeholder_script(
            sp_name=sp_name,
            sp_definition=sp_definition,
            classification=SPClassification.COMPLEX,
            complexity_elements=classification_result.complexity_elements,
            reason="Complex SP - requires manual conversion",
        )

        return SPRewriteResult(
            success=False,
            original_sp_name=sp_name,
            classification=SPClassification.COMPLEX,
            confidence=ConfidenceLevel.NA,
            converted_sql=placeholder_sql,
            complexity_elements=classification_result.complexity_elements,
            error_message="Complex SP requires manual conversion",
            validation_suggestions=self._generate_validation_suggestions(
                ConfidenceLevel.NA
            ),
        )

    async def rewrite_with_ai(
        self,
        sp_name: str,
        sp_definition: Optional[str] = None,
        sp_call: Optional[str] = None,
    ) -> tuple[SPRewriteResult, Optional["AIRewriteAttempt"]]:
        """Rewrite a stored procedure with AI assistance for complex SPs.

        This async method attempts AI-assisted rewriting for moderate and
        complex stored procedures when AI is enabled.

        Args:
            sp_name: Name of the stored procedure
            sp_definition: Full SP definition (CREATE PROCEDURE ...)
            sp_call: The SP call syntax (EXEC sp_name @param1, @param2)

        Returns:
            Tuple of (SPRewriteResult, AIRewriteAttempt or None)
        """
        if not sp_definition:
            # No definition available - generate placeholder
            return self._generate_placeholder(
                sp_name=sp_name,
                sp_call=sp_call,
                reason="SP definition not available",
            ), None

        # Parse and classify
        parser = SPParser(sp_definition)
        classifier = SPClassifier(parser)
        classification_result = classifier.classify()

        # Simple SPs use rule-based conversion
        if classification_result.classification == SPClassification.SIMPLE:
            return self._rewrite_simple(
                sp_name=sp_name,
                sp_definition=sp_definition,
                parser=parser,
                classification_result=classification_result,
            ), None

        # For moderate and complex, try AI if enabled
        if self.enable_ai:
            parameters = self._extract_sp_parameters(sp_definition)
            ai_rewriter = self._get_ai_rewriter()

            try:
                result, attempt = await ai_rewriter.rewrite(
                    sp_name=sp_name,
                    sp_definition=sp_definition,
                    classification=classification_result.classification,
                    parameters=parameters,
                )

                if result.success:
                    return result, attempt

                # AI failed, fall through to rule-based
                logger.info(
                    "AI rewrite failed for %s, falling back to rule-based: %s",
                    sp_name,
                    result.error_message,
                )
            except Exception as e:
                logger.exception("AI rewrite error for %s: %s", sp_name, str(e))

        # Fall back to rule-based for moderate
        if classification_result.classification == SPClassification.MODERATE:
            return self._rewrite_moderate(
                sp_name=sp_name,
                sp_definition=sp_definition,
                parser=parser,
                classification_result=classification_result,
            ), None

        # Complex falls back to placeholder
        return self._handle_complex(
            sp_name=sp_name,
            sp_definition=sp_definition,
            classification_result=classification_result,
        ), None

    def _generate_placeholder(
        self,
        sp_name: str,
        sp_call: Optional[str],
        reason: str,
    ) -> SPRewriteResult:
        """Generate a placeholder for SP without definition.

        Args:
            sp_name: Name of the SP
            sp_call: The SP call syntax
            reason: Reason for placeholder

        Returns:
            SPRewriteResult with placeholder
        """
        placeholder_sql = self._generate_placeholder_script(
            sp_name=sp_name,
            sp_definition=None,
            classification=SPClassification.COMPLEX,
            complexity_elements=[],
            reason=reason,
            sp_call=sp_call,
        )

        return SPRewriteResult(
            success=False,
            original_sp_name=sp_name,
            classification=SPClassification.COMPLEX,
            confidence=ConfidenceLevel.NA,
            converted_sql=placeholder_sql,
            error_message=reason,
            validation_suggestions=self._generate_validation_suggestions(
                ConfidenceLevel.NA
            ),
        )

    def _generate_parameter_declarations(
        self,
        parameters: list[SPParameter],
    ) -> str:
        """Generate Snowflake parameter declarations.

        Args:
            parameters: List of SP parameters

        Returns:
            Parameter declaration SQL
        """
        if not parameters:
            return ""

        lines = ["-- Parameter Declarations"]
        for param in parameters:
            param_name = param.name.lower()
            snowflake_type = self.sql_generator._map_data_type(param.data_type)

            if param.default_value:
                default = param.default_value
                # Convert common defaults
                if default.upper() in ("NULL", "GETDATE()", "CURRENT_TIMESTAMP"):
                    if default.upper() == "GETDATE()":
                        default = "CURRENT_TIMESTAMP()"
                    elif default.upper() == "NULL":
                        default = "NULL"
                lines.append(
                    f"SET {param_name} = {default}; -- @{param.name} ({param.data_type})"
                )
            else:
                # Use a placeholder value based on type
                if snowflake_type in ("INTEGER", "NUMBER", "DECIMAL"):
                    default = "0"
                elif snowflake_type in ("VARCHAR", "STRING", "TEXT"):
                    default = "''"
                elif snowflake_type in ("TIMESTAMP", "DATE"):
                    default = "CURRENT_DATE()"
                elif snowflake_type == "BOOLEAN":
                    default = "FALSE"
                else:
                    default = "NULL"
                lines.append(
                    f"SET {param_name} = {default}; -- @{param.name} ({param.data_type})"
                )

        return "\n".join(lines)

    def _generate_script(
        self,
        sp_name: str,
        classification: SPClassification,
        confidence: ConfidenceLevel,
        param_declarations: str,
        converted_sql: str,
        function_count: int = 0,
    ) -> str:
        """Generate the full converted SQL script.

        Args:
            sp_name: Original SP name
            classification: SP classification
            confidence: Confidence level
            param_declarations: Parameter declaration SQL
            converted_sql: Converted query SQL
            function_count: Number of functions converted

        Returns:
            Full formatted SQL script
        """
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        lines = [
            "-- ============================================",
            "-- ReportLift SP Conversion Script",
            f"-- Generated: {timestamp}",
            f"-- Original SP: {sp_name}",
            f"-- Classification: {classification.value}",
            f"-- Confidence: {confidence.value}",
            f"-- Target: Snowflake",
            f"-- Warehouse: {self.warehouse}",
            f"-- Database: {self.database}",
            f"-- Schema: {self.schema}",
            "-- ============================================",
            "",
        ]

        if function_count > 0:
            lines.append(f"-- Conversion Notes: {function_count} function(s) mapped")
            lines.append("")

        if param_declarations:
            lines.append(param_declarations)
            lines.append("")

        lines.append("-- Converted Query")
        lines.append(converted_sql)

        if not converted_sql.rstrip().endswith(";"):
            lines.append(";")

        return "\n".join(lines)

    def _generate_placeholder_script(
        self,
        sp_name: str,
        sp_definition: Optional[str],
        classification: SPClassification,
        complexity_elements: list[ComplexityElement],
        reason: str,
        sp_call: Optional[str] = None,
    ) -> str:
        """Generate a placeholder script for SPs that cannot be auto-converted.

        Args:
            sp_name: Original SP name
            sp_definition: Full SP definition (if available)
            classification: SP classification
            complexity_elements: List of detected complexity elements
            reason: Reason for placeholder
            sp_call: The SP call syntax (if available)

        Returns:
            Placeholder SQL script
        """
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        lines = [
            "-- ============================================",
            "-- ReportLift SP Conversion Script",
            f"-- Generated: {timestamp}",
            f"-- Original SP: {sp_name}",
            f"-- Classification: {classification.value}",
            "-- Confidence: N/A (Manual conversion required)",
            "-- ============================================",
            "",
        ]

        if complexity_elements:
            lines.append("-- Detected Complexity Elements:")
            for elem in complexity_elements:
                lines.append(f"--   - {elem.description}")
            lines.append("")

        lines.append(f"-- TODO: Manual conversion required for {sp_name}")
        lines.append(f"-- Reason: {reason}")
        lines.append("")

        if sp_call:
            lines.append("-- Original SP Call:")
            lines.append(f"-- {sp_call}")
            lines.append("")

        if sp_definition:
            lines.append("-- Original SP definition preserved below for reference:")
            lines.append("/*")
            lines.append(sp_definition)
            lines.append("*/")
            lines.append("")

        lines.append("-- Placeholder query (replace with converted logic):")
        lines.append(
            f"SELECT 'TODO: Implement converted query for {sp_name}' AS status;"
        )

        return "\n".join(lines)

    def _generate_validation_suggestions(
        self,
        confidence: ConfidenceLevel,
    ) -> list[str]:
        """Generate validation suggestions based on confidence level.

        Args:
            confidence: Confidence level of the rewrite

        Returns:
            List of validation suggestions
        """
        base_suggestions = [
            "Compare row counts between original SP and converted query",
            "Sample 100 random rows and verify data matches",
        ]

        if confidence == ConfidenceLevel.HIGH:
            return base_suggestions + [
                "Test with typical parameter values",
            ]
        elif confidence == ConfidenceLevel.MEDIUM:
            return base_suggestions + [
                "Test with edge case parameters (null, empty, boundary values)",
                "Verify UNION logic produces expected results",
                "Check for NULL handling differences between SQL Server and Snowflake",
            ]
        elif confidence == ConfidenceLevel.LOW:
            return base_suggestions + [
                "Thoroughly review converted query logic",
                "Test all conditional branches",
                "Compare execution time for performance baseline",
                "Consider manual review by database expert",
            ]
        else:  # N/A
            return [
                "Full manual conversion required",
                "Review original SP logic carefully",
                "Document all business rules implemented in SP",
                "Create comprehensive test cases before implementing",
                "Consider breaking complex SP into multiple simpler queries",
            ]


def classify_stored_procedure(sp_definition: str) -> SPClassificationResult:
    """Convenience function to classify a stored procedure.

    Args:
        sp_definition: Full SP definition

    Returns:
        Classification result
    """
    parser = SPParser(sp_definition)
    classifier = SPClassifier(parser)
    return classifier.classify()


def rewrite_stored_procedure(
    sp_name: str,
    sp_definition: Optional[str] = None,
    sp_call: Optional[str] = None,
    database: Optional[str] = None,
    schema: Optional[str] = None,
    warehouse: Optional[str] = None,
) -> SPRewriteResult:
    """Convenience function to rewrite a stored procedure.

    Args:
        sp_name: Name of the stored procedure
        sp_definition: Full SP definition (CREATE PROCEDURE ...)
        sp_call: The SP call syntax (EXEC sp_name @param1, @param2)
        database: Target Snowflake database
        schema: Target Snowflake schema
        warehouse: Target Snowflake warehouse

    Returns:
        SPRewriteResult with rewrite details
    """
    rewriter = SPRewriter(
        database=database,
        schema=schema,
        warehouse=warehouse,
    )
    return rewriter.rewrite(
        sp_name=sp_name,
        sp_definition=sp_definition,
        sp_call=sp_call,
    )
