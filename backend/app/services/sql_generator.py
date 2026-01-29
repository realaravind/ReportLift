"""SQL Generator Service - Converts SQL Server queries to Snowflake syntax.

This module provides SQL conversion from SQL Server to Snowflake, including:
- Function mapping (GETDATE -> CURRENT_TIMESTAMP, etc.)
- Schema qualification (database.schema.table)
- Parameter conversion to Snowflake session variables
- Output file generation
"""

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import sqlparse
from sqlparse.tokens import Keyword, Name, Punctuation

from app.schemas.analysis import DatasetFeature, DatasetParameter, QueryType

logger = logging.getLogger(__name__)


@dataclass
class FunctionMapping:
    """Record of a function conversion."""

    original: str
    converted: str
    pattern: str
    notes: str = ""


@dataclass
class ConversionResult:
    """Result of converting a single SQL query."""

    original_sql: str
    converted_sql: str
    function_mappings: list[FunctionMapping] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    has_unconverted_functions: bool = False


@dataclass
class SQLScriptOutput:
    """Output file information for a generated SQL script."""

    filename: str
    dataset_name: str
    content: str
    size_bytes: int
    function_count: int
    warning_count: int


@dataclass
class SQLGenerationResult:
    """Complete result of SQL generation for a conversion job."""

    scripts: list[SQLScriptOutput] = field(default_factory=list)
    all_scripts_path: str = ""
    total_functions_mapped: int = 0
    total_warnings: int = 0
    datasets_processed: int = 0


# SQL Server to Snowflake function mappings
# Pattern: (regex_pattern, replacement, notes)
FUNCTION_MAPPINGS: list[tuple[str, str, str]] = [
    # Date/Time functions
    (r"\bGETDATE\s*\(\s*\)", "CURRENT_TIMESTAMP()", "Date/time function"),
    (r"\bGETUTCDATE\s*\(\s*\)", "CURRENT_TIMESTAMP()", "UTC date/time"),
    (r"\bSYSDATETIME\s*\(\s*\)", "CURRENT_TIMESTAMP()", "System date/time"),
    (r"\bSYSUTCDATETIME\s*\(\s*\)", "CURRENT_TIMESTAMP()", "System UTC date/time"),

    # Null handling
    (r"\bISNULL\s*\(", "COALESCE(", "Null handling"),

    # String functions
    (r"\bLEN\s*\(", "LENGTH(", "String length"),
    # CHARINDEX(search, string) -> POSITION(search IN string) - simple case only
    (r"\bCHARINDEX\s*\(\s*('[^']*')\s*,\s*(\w+)\s*\)", r"POSITION(\1 IN \2)", "String search"),
    (r"\bSUBSTRING\s*\(", "SUBSTR(", "Substring extraction"),
    (r"\bSTUFF\s*\(", "INSERT(", "String insert/replace"),
    (r"\bLTRIM\s*\(RTRIM\s*\((\w+)\)\)", r"TRIM(\1)", "Trim both sides"),
    (r"\bREPLICATE\s*\(", "REPEAT(", "String repeat"),
    (r"\bSPACE\s*\(", "REPEAT(' ', ", "Space padding"),
    (r"\bREVERSE\s*\(", "REVERSE(", "String reverse"),

    # Type conversion - CONVERT to CAST (using simple identifier patterns)
    # CONVERT(datatype, expression) -> CAST(expression AS datatype)
    (r"\bCONVERT\s*\(\s*VARCHAR(?:\(\d+\))?\s*,\s*(\w+)\s*\)", r"CAST(\1 AS VARCHAR)", "VARCHAR conversion"),
    (r"\bCONVERT\s*\(\s*NVARCHAR(?:\(\d+\))?\s*,\s*(\w+)\s*\)", r"CAST(\1 AS VARCHAR)", "NVARCHAR conversion"),
    (r"\bCONVERT\s*\(\s*INT\s*,\s*(\w+)\s*\)", r"CAST(\1 AS INTEGER)", "INT conversion"),
    (r"\bCONVERT\s*\(\s*INTEGER\s*,\s*(\w+)\s*\)", r"CAST(\1 AS INTEGER)", "INTEGER conversion"),
    (r"\bCONVERT\s*\(\s*BIGINT\s*,\s*(\w+)\s*\)", r"CAST(\1 AS BIGINT)", "BIGINT conversion"),
    (r"\bCONVERT\s*\(\s*DECIMAL(?:\(\d+(?:,\d+)?\))?\s*,\s*(\w+)\s*\)", r"CAST(\1 AS DECIMAL)", "DECIMAL conversion"),
    (r"\bCONVERT\s*\(\s*NUMERIC(?:\(\d+(?:,\d+)?\))?\s*,\s*(\w+)\s*\)", r"CAST(\1 AS NUMERIC)", "NUMERIC conversion"),
    (r"\bCONVERT\s*\(\s*FLOAT\s*,\s*(\w+)\s*\)", r"CAST(\1 AS FLOAT)", "FLOAT conversion"),
    (r"\bCONVERT\s*\(\s*DATE\s*,\s*(\w+)\s*\)", r"CAST(\1 AS DATE)", "DATE conversion"),
    (r"\bCONVERT\s*\(\s*DATETIME\s*,\s*(\w+)\s*\)", r"CAST(\1 AS TIMESTAMP)", "DATETIME conversion"),
    (r"\bCONVERT\s*\(\s*BIT\s*,\s*(\w+)\s*\)", r"CAST(\1 AS BOOLEAN)", "BIT conversion"),

    # Math functions
    (r"\bCEILING\s*\(", "CEIL(", "Ceiling function"),
    (r"\bRAND\s*\(\s*\)", "RANDOM()", "Random number"),
    (r"\bSQUARE\s*\(([^)]+)\)", r"POWER(\1, 2)", "Square function"),

    # Aggregate functions - mostly compatible
    (r"\bCOUNT_BIG\s*\(", "COUNT(", "Count big"),

    # Logical functions
    (r"\bIIF\s*\(", "IFF(", "Inline if"),

    # JSON functions (SQL Server 2016+)
    (r"\bJSON_VALUE\s*\(", "JSON_EXTRACT_PATH_TEXT(", "JSON value extraction"),
    (r"\bJSON_QUERY\s*\(", "PARSE_JSON(", "JSON query"),

    # Window functions - mostly compatible, just syntax differences
    (r"\bROW_NUMBER\s*\(\s*\)\s*OVER\s*\(", "ROW_NUMBER() OVER (", "Row number"),
]

# TOP N to LIMIT N conversion (special handling needed)
TOP_PATTERN = re.compile(r"\bSELECT\s+TOP\s+(\d+)\s+", re.IGNORECASE)

# String concatenation: + to ||
STRING_CONCAT_PATTERN = re.compile(r"('(?:[^']*(?:'')*[^']*)*')\s*\+\s*", re.IGNORECASE)


class SQLGenerator:
    """Generates Snowflake SQL scripts from SQL Server queries."""

    def __init__(
        self,
        database: str = "PLACEHOLDER_DATABASE",
        schema: str = "PLACEHOLDER_SCHEMA",
        warehouse: str = "PLACEHOLDER_WAREHOUSE",
    ):
        """Initialize the SQL generator.

        Args:
            database: Snowflake database name
            schema: Snowflake schema name
            warehouse: Snowflake warehouse name
        """
        self.database = database
        self.schema = schema
        self.warehouse = warehouse
        self._compiled_patterns: list[tuple[re.Pattern, str, str]] = []
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for better performance."""
        for pattern, replacement, notes in FUNCTION_MAPPINGS:
            self._compiled_patterns.append(
                (re.compile(pattern, re.IGNORECASE), replacement, notes)
            )

    def convert_sql(self, sql: str) -> ConversionResult:
        """Convert SQL Server query to Snowflake syntax.

        Args:
            sql: SQL Server query string

        Returns:
            ConversionResult with converted SQL and mapping details
        """
        if not sql or not sql.strip():
            return ConversionResult(
                original_sql=sql,
                converted_sql=sql,
            )

        converted = sql
        mappings: list[FunctionMapping] = []
        warnings: list[str] = []

        # Apply function mappings
        for pattern, replacement, notes in self._compiled_patterns:
            matches = pattern.findall(converted)
            if matches:
                for match in matches if isinstance(matches[0], str) else [m[0] for m in matches]:
                    original_func = match if isinstance(match, str) else str(match)
                    mappings.append(FunctionMapping(
                        original=original_func[:50],  # Truncate for readability
                        converted=replacement[:50],
                        pattern=pattern.pattern[:50],
                        notes=notes,
                    ))
                converted = pattern.sub(replacement, converted)

        # Handle TOP N -> LIMIT N
        converted, top_mapped = self._convert_top_to_limit(converted)
        if top_mapped:
            mappings.append(FunctionMapping(
                original="TOP N",
                converted="LIMIT N",
                pattern="SELECT TOP N",
                notes="Moved to end of query",
            ))

        # Handle string concatenation (+ to ||)
        converted, concat_count = self._convert_string_concat(converted)
        if concat_count > 0:
            mappings.append(FunctionMapping(
                original="+ (string)",
                converted="||",
                pattern="string + string",
                notes=f"{concat_count} concatenation(s) converted",
            ))

        # Check for unconverted SQL Server functions
        unconverted = self._find_unconverted_functions(converted)
        if unconverted:
            for func in unconverted:
                warnings.append(f"Unconverted SQL Server function: {func}")

        # Format the SQL
        converted = self._format_sql(converted)

        return ConversionResult(
            original_sql=sql,
            converted_sql=converted,
            function_mappings=mappings,
            warnings=warnings,
            has_unconverted_functions=len(unconverted) > 0,
        )

    def _convert_top_to_limit(self, sql: str) -> tuple[str, bool]:
        """Convert SELECT TOP N to SELECT ... LIMIT N.

        Args:
            sql: SQL query string

        Returns:
            Tuple of (converted SQL, whether conversion was applied)
        """
        match = TOP_PATTERN.search(sql)
        if not match:
            return sql, False

        limit_value = match.group(1)
        # Remove TOP N from SELECT
        converted = TOP_PATTERN.sub("SELECT ", sql)
        # Add LIMIT at the end (before any trailing semicolon)
        converted = converted.rstrip().rstrip(";")
        converted = f"{converted}\nLIMIT {limit_value};"

        return converted, True

    def _convert_string_concat(self, sql: str) -> tuple[str, int]:
        """Convert string concatenation from + to ||.

        This is conservative - only converts when we're sure it's string concat.

        Args:
            sql: SQL query string

        Returns:
            Tuple of (converted SQL, number of conversions)
        """
        # Simple approach: look for patterns like 'text' + or + 'text'
        # Use simple patterns to avoid catastrophic backtracking
        count = 0

        # Pattern: 'simple string' + (no escaped quotes for safety)
        pattern1 = re.compile(r"('[^']*')\s*\+\s*")
        matches = pattern1.findall(sql)
        if matches:
            sql = pattern1.sub(r"\1 || ", sql)
            count += len(matches)

        # Pattern: + 'simple string'
        pattern2 = re.compile(r"\s*\+\s*('[^']*')")
        matches = pattern2.findall(sql)
        if matches:
            sql = pattern2.sub(r" || \1", sql)
            count += len(matches)

        return sql, count

    def _find_unconverted_functions(self, sql: str) -> list[str]:
        """Find SQL Server functions that weren't converted.

        Args:
            sql: Converted SQL query

        Returns:
            List of unconverted function names
        """
        # Common SQL Server functions that might not be converted
        sql_server_functions = [
            "GETDATE", "GETUTCDATE", "SYSDATETIME",
            "ISNULL", "CHARINDEX", "STUFF",
            "CONVERT", "IIF", "NEWID",
            "PATINDEX", "QUOTENAME", "SOUNDEX",
            "FORMAT",  # SQL Server 2012+
        ]

        unconverted = []
        for func in sql_server_functions:
            pattern = re.compile(rf"\b{func}\s*\(", re.IGNORECASE)
            if pattern.search(sql):
                unconverted.append(func)

        return unconverted

    def _format_sql(self, sql: str) -> str:
        """Format SQL for readability.

        Args:
            sql: SQL query string

        Returns:
            Formatted SQL string
        """
        try:
            formatted = sqlparse.format(
                sql,
                reindent=True,
                keyword_case="upper",
                identifier_case="lower",
                indent_width=4,
            )
            return formatted
        except Exception as e:
            logger.warning("SQL formatting failed: %s", e)
            return sql

    def qualify_table_references(self, sql: str) -> str:
        """Add database.schema prefix to table references.

        This is a simple implementation that adds schema prefix.
        More complex parsing would be needed for complete accuracy.

        Args:
            sql: SQL query string

        Returns:
            SQL with qualified table references
        """
        # Add schema prefix in FROM and JOIN clauses
        # This is a simplified approach - production would need full SQL parsing

        # Pattern to match FROM/JOIN followed by table name (not already qualified)
        from_pattern = re.compile(
            r"(\bFROM\s+)(?![\w]+\.[\w]+\.)([\w]+)(\s|$|,|\))",
            re.IGNORECASE
        )
        join_pattern = re.compile(
            r"(\bJOIN\s+)(?![\w]+\.[\w]+\.)([\w]+)(\s|$|\))",
            re.IGNORECASE
        )

        qualified = from_pattern.sub(
            rf"\1{self.database}.{self.schema}.\2\3",
            sql
        )
        qualified = join_pattern.sub(
            rf"\1{self.database}.{self.schema}.\2\3",
            qualified
        )

        return qualified

    def convert_parameters(
        self,
        parameters: list[DatasetParameter],
    ) -> str:
        """Generate Snowflake SET statements for parameters.

        Args:
            parameters: List of dataset parameters

        Returns:
            SQL SET statements for parameters
        """
        if not parameters:
            return ""

        lines = ["-- Parameter Declarations"]
        for param in parameters:
            name = param.name.lower()
            default = self._convert_parameter_default(param)
            data_type = self._map_data_type(param.data_type)

            comment = ""
            if param.default_value:
                comment = f" -- Default from RDL: {param.default_value}"

            lines.append(f"SET {name} = {default};{comment}")

        lines.append("")  # Empty line after parameters
        return "\n".join(lines)

    def _convert_parameter_default(self, param: DatasetParameter) -> str:
        """Convert RDL parameter default to Snowflake expression.

        Args:
            param: Dataset parameter

        Returns:
            Snowflake expression for default value
        """
        default = param.default_value

        if not default:
            # Generate appropriate default based on type
            data_type = (param.data_type or "").lower()
            if "date" in data_type or "time" in data_type:
                return "CURRENT_DATE()"
            elif "int" in data_type or "decimal" in data_type or "numeric" in data_type:
                return "0"
            elif "bool" in data_type or "bit" in data_type:
                return "FALSE"
            else:
                return "''"

        # Convert RDL expression defaults
        default_lower = default.lower()
        if "today()" in default_lower or "=today()" in default_lower:
            return "CURRENT_DATE()"
        elif "now()" in default_lower or "=now()" in default_lower:
            return "CURRENT_TIMESTAMP()"
        elif default.startswith("="):
            # Complex expression - return as placeholder
            return f"NULL /* TODO: Convert expression: {default} */"
        else:
            # Literal value
            if param.data_type and "char" in param.data_type.lower():
                return f"'{default}'"
            return default

    def _map_data_type(self, data_type: str | None) -> str:
        """Map SQL Server data type to Snowflake.

        Args:
            data_type: SQL Server data type

        Returns:
            Snowflake data type
        """
        if not data_type:
            return "VARCHAR"

        type_lower = data_type.lower()

        # Ordered from most specific to least specific to avoid substring matches
        type_mapping = [
            ("datetime2", "TIMESTAMP"),
            ("smalldatetime", "TIMESTAMP"),
            ("datetime", "TIMESTAMP"),
            ("date", "DATE"),
            ("time", "TIME"),
            ("bit", "BOOLEAN"),
            ("tinyint", "SMALLINT"),
            ("smallint", "SMALLINT"),
            ("bigint", "BIGINT"),
            ("int", "INTEGER"),
            ("decimal", "DECIMAL"),
            ("numeric", "NUMERIC"),
            ("smallmoney", "DECIMAL(10,4)"),
            ("money", "DECIMAL(19,4)"),
            ("float", "FLOAT"),
            ("real", "FLOAT"),
            ("nvarchar", "VARCHAR"),  # Check before varchar
            ("varchar", "VARCHAR"),
            ("nchar", "CHAR"),  # Check before char
            ("char", "CHAR"),
            ("ntext", "VARCHAR"),
            ("text", "VARCHAR"),
            ("uniqueidentifier", "VARCHAR(36)"),
            ("xml", "VARIANT"),
            ("varbinary", "BINARY"),
            ("binary", "BINARY"),
            ("image", "BINARY"),
            ("string", "VARCHAR"),  # RDL/SSRS type
            ("boolean", "BOOLEAN"),  # RDL type
        ]

        for sql_type, snow_type in type_mapping:
            if sql_type in type_lower:
                return snow_type

        return "VARCHAR"

    def generate_script_header(
        self,
        report_name: str,
        dataset_name: str,
        query_type: QueryType,
        function_count: int = 0,
    ) -> str:
        """Generate header comment for SQL script.

        Args:
            report_name: Name of the source report
            dataset_name: Name of the dataset
            query_type: Type of query (embedded SQL, stored procedure, etc.)
            function_count: Number of functions converted

        Returns:
            Header comment string
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        header = f"""-- ============================================
-- ReportLift SQL Script
-- Generated: {timestamp}
-- Report: {report_name}
-- Dataset: {dataset_name}
-- Target: Snowflake
-- Warehouse: {self.warehouse}
-- Database: {self.database}
-- Schema: {self.schema}
-- ============================================

-- Original Query Type: {query_type.value.replace('_', ' ').title()}
-- Conversion Notes: {function_count} function(s) mapped

"""
        return header

    def generate_sp_placeholder(
        self,
        sp_name: str,
        dataset_name: str,
        report_name: str,
    ) -> str:
        """Generate placeholder script for complex stored procedure.

        Args:
            sp_name: Stored procedure name
            dataset_name: Dataset name
            report_name: Report name

        Returns:
            Placeholder SQL script with TODO comments
        """
        header = self.generate_script_header(
            report_name=report_name,
            dataset_name=dataset_name,
            query_type=QueryType.STORED_PROCEDURE,
            function_count=0,
        )

        placeholder = f"""{header}
-- ===========================================
-- TODO: MANUAL CONVERSION REQUIRED
-- ===========================================
-- This dataset uses a stored procedure that requires manual conversion.
--
-- Original Stored Procedure: {sp_name}
--
-- Steps to convert:
-- 1. Locate the original stored procedure in SQL Server
-- 2. Analyze the logic and dependencies
-- 3. Convert to Snowflake-compatible SQL or Snowflake Stored Procedure
-- 4. Replace this placeholder with the converted code
--
-- Notes:
-- - Consider using Snowflake JavaScript or Python stored procedures
-- - Check for cursor operations (not supported in Snowflake SQL)
-- - Validate temp table usage patterns
-- - Review transaction handling differences
-- ===========================================

-- Placeholder query (returns empty result set)
SELECT
    'TODO: Convert stored procedure {sp_name}' AS conversion_note,
    NULL AS placeholder_column
WHERE 1 = 0;
"""
        return placeholder


def generate_sql_scripts(
    datasets: list[DatasetFeature],
    report_name: str,
    output_dir: str,
    database: str = "PLACEHOLDER_DATABASE",
    schema: str = "PLACEHOLDER_SCHEMA",
    warehouse: str = "PLACEHOLDER_WAREHOUSE",
) -> SQLGenerationResult:
    """Generate SQL scripts for all datasets in a report.

    Args:
        datasets: List of dataset features from analysis
        report_name: Name of the report
        output_dir: Directory to write output files
        database: Snowflake database name
        schema: Snowflake schema name
        warehouse: Snowflake warehouse name

    Returns:
        SQLGenerationResult with generated script information
    """
    generator = SQLGenerator(database=database, schema=schema, warehouse=warehouse)

    result = SQLGenerationResult()
    all_scripts_content: list[str] = []

    # Header for combined file
    all_scripts_header = f"""-- ============================================
-- ReportLift Combined SQL Scripts
-- Generated: {datetime.now(timezone.utc).isoformat()}
-- Report: {report_name}
-- Target: Snowflake
-- Warehouse: {warehouse}
-- Database: {database}
-- Schema: {schema}
-- Datasets: {len(datasets)}
-- ============================================

"""
    all_scripts_content.append(all_scripts_header)

    # Create output directory
    sql_dir = os.path.join(output_dir, "sql")
    os.makedirs(sql_dir, exist_ok=True)

    for dataset in datasets:
        script_content = ""
        conversion_result: ConversionResult | None = None

        if dataset.query_type == QueryType.STORED_PROCEDURE:
            # Generate placeholder for stored procedures
            script_content = generator.generate_sp_placeholder(
                sp_name=dataset.stored_procedure_name or "Unknown",
                dataset_name=dataset.name,
                report_name=report_name,
            )
        elif dataset.query_type == QueryType.EMBEDDED_SQL and dataset.command_text:
            # Convert embedded SQL
            conversion_result = generator.convert_sql(dataset.command_text)

            # Generate header
            header = generator.generate_script_header(
                report_name=report_name,
                dataset_name=dataset.name,
                query_type=dataset.query_type,
                function_count=len(conversion_result.function_mappings),
            )

            # Generate parameter declarations
            param_section = generator.convert_parameters(dataset.parameters)

            # Qualify table references
            converted_sql = generator.qualify_table_references(
                conversion_result.converted_sql
            )

            # Combine parts
            script_content = f"{header}{param_section}-- Converted Query\n{converted_sql}\n"

            # Add warnings as comments
            if conversion_result.warnings:
                script_content += "\n-- Warnings:\n"
                for warning in conversion_result.warnings:
                    script_content += f"-- {warning}\n"

        elif dataset.query_type == QueryType.SHARED_DATASET:
            # Shared datasets reference another dataset
            script_content = generator.generate_script_header(
                report_name=report_name,
                dataset_name=dataset.name,
                query_type=dataset.query_type,
                function_count=0,
            )
            script_content += f"""
-- This is a shared dataset reference.
-- The actual query is defined in the shared dataset.
-- Data Source: {dataset.data_source_name or 'Not specified'}

-- TODO: Locate and convert the shared dataset definition
"""

        # Skip empty datasets
        if not script_content:
            continue

        # Write individual file
        filename = f"{dataset.name.lower().replace(' ', '_')}.sql"
        filepath = os.path.join(sql_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(script_content)

        # Track output
        script_output = SQLScriptOutput(
            filename=filename,
            dataset_name=dataset.name,
            content=script_content,
            size_bytes=len(script_content.encode("utf-8")),
            function_count=len(conversion_result.function_mappings) if conversion_result else 0,
            warning_count=len(conversion_result.warnings) if conversion_result else 0,
        )
        result.scripts.append(script_output)
        result.datasets_processed += 1

        if conversion_result:
            result.total_functions_mapped += len(conversion_result.function_mappings)
            result.total_warnings += len(conversion_result.warnings)

        # Add to combined file
        all_scripts_content.append(f"\n-- {'=' * 50}\n")
        all_scripts_content.append(f"-- Dataset: {dataset.name}\n")
        all_scripts_content.append(f"-- {'=' * 50}\n\n")
        all_scripts_content.append(script_content)
        all_scripts_content.append("\n")

    # Write combined file
    all_scripts_path = os.path.join(sql_dir, "all_scripts.sql")
    combined_content = "".join(all_scripts_content)

    with open(all_scripts_path, "w", encoding="utf-8") as f:
        f.write(combined_content)

    result.all_scripts_path = all_scripts_path

    logger.info(
        "Generated %d SQL scripts for report '%s' (%d functions mapped, %d warnings)",
        result.datasets_processed,
        report_name,
        result.total_functions_mapped,
        result.total_warnings,
    )

    return result
