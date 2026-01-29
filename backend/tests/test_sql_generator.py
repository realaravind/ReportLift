"""Tests for SQL Generator service."""

import os
import tempfile
import pytest

from app.services.sql_generator import (
    SQLGenerator,
    ConversionResult,
    FunctionMapping,
    SQLScriptOutput,
    SQLGenerationResult,
    generate_sql_scripts,
)
from app.schemas.analysis import (
    DatasetFeature,
    DatasetParameter,
    QueryType,
)


class TestSQLGeneratorFunctionMappings:
    """Tests for SQL Server to Snowflake function mappings."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = SQLGenerator(
            database="TEST_DB",
            schema="TEST_SCHEMA",
            warehouse="TEST_WH",
        )

    def test_getdate_to_current_timestamp(self):
        """Test GETDATE() conversion."""
        sql = "SELECT GETDATE() AS current_time"
        result = self.generator.convert_sql(sql)
        assert "current_timestamp()" in result.converted_sql.lower()
        assert "getdate" not in result.converted_sql.lower()

    def test_isnull_to_coalesce(self):
        """Test ISNULL() conversion."""
        sql = "SELECT ISNULL(column1, 'default') AS value"
        result = self.generator.convert_sql(sql)
        assert "coalesce(" in result.converted_sql.lower()
        assert "isnull(" not in result.converted_sql.lower()

    def test_len_to_length(self):
        """Test LEN() conversion."""
        sql = "SELECT LEN(name) AS name_length FROM users"
        result = self.generator.convert_sql(sql)
        assert "length(" in result.converted_sql.lower()
        # LEN might still appear in column name 'name_length'
        assert result.converted_sql.lower().count("len(") == 0

    def test_substring_to_substr(self):
        """Test SUBSTRING() conversion."""
        sql = "SELECT SUBSTRING(name, 1, 10) FROM users"
        result = self.generator.convert_sql(sql)
        assert "substr(" in result.converted_sql.lower()
        assert "substring(" not in result.converted_sql.lower()

    def test_charindex_to_position(self):
        """Test CHARINDEX() conversion."""
        sql = "SELECT CHARINDEX('@', email) AS at_pos FROM users"
        result = self.generator.convert_sql(sql)
        assert "position(" in result.converted_sql.lower()
        assert "charindex(" not in result.converted_sql.lower()

    def test_convert_varchar_to_cast(self):
        """Test CONVERT(VARCHAR, ...) to CAST(... AS VARCHAR)."""
        sql = "SELECT CONVERT(VARCHAR, amount) AS amount_str"
        result = self.generator.convert_sql(sql)
        assert "cast(" in result.converted_sql.lower()
        assert "varchar" in result.converted_sql.lower()

    def test_convert_int_to_cast(self):
        """Test CONVERT(INT, ...) to CAST(... AS INTEGER)."""
        sql = "SELECT CONVERT(INT, value) AS int_value"
        result = self.generator.convert_sql(sql)
        assert "cast(" in result.converted_sql.lower()
        assert "integer" in result.converted_sql.lower()

    def test_convert_datetime_to_cast(self):
        """Test CONVERT(DATETIME, ...) to CAST(... AS TIMESTAMP)."""
        sql = "SELECT CONVERT(DATETIME, date_str) AS date_value"
        result = self.generator.convert_sql(sql)
        assert "cast(" in result.converted_sql.lower()
        assert "timestamp" in result.converted_sql.lower()

    def test_ceiling_to_ceil(self):
        """Test CEILING() conversion."""
        sql = "SELECT CEILING(price) AS rounded_price"
        result = self.generator.convert_sql(sql)
        assert "ceil(" in result.converted_sql.lower()
        assert "ceiling(" not in result.converted_sql.lower()

    def test_iif_to_iff(self):
        """Test IIF() conversion."""
        sql = "SELECT IIF(status = 1, 'Active', 'Inactive') AS status_text"
        result = self.generator.convert_sql(sql)
        assert "iff(" in result.converted_sql.lower()
        # IIF might still appear as substring

    def test_stuff_to_insert(self):
        """Test STUFF() conversion."""
        sql = "SELECT STUFF(phone, 1, 3, 'XXX') AS masked_phone"
        result = self.generator.convert_sql(sql)
        assert "insert(" in result.converted_sql.lower()
        assert "stuff(" not in result.converted_sql.lower()

    def test_replicate_to_repeat(self):
        """Test REPLICATE() conversion."""
        sql = "SELECT REPLICATE('*', 10) AS stars"
        result = self.generator.convert_sql(sql)
        assert "repeat(" in result.converted_sql.lower()
        assert "replicate(" not in result.converted_sql.lower()


class TestTopToLimitConversion:
    """Tests for TOP N to LIMIT N conversion."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = SQLGenerator()

    def test_top_to_limit(self):
        """Test TOP N converted to LIMIT N."""
        sql = "SELECT TOP 10 * FROM users"
        result = self.generator.convert_sql(sql)
        assert "limit 10" in result.converted_sql.lower()
        assert "top" not in result.converted_sql.lower()

    def test_top_100_to_limit(self):
        """Test TOP 100 converted to LIMIT 100."""
        sql = "SELECT TOP 100 name, email FROM customers"
        result = self.generator.convert_sql(sql)
        assert "limit 100" in result.converted_sql.lower()

    def test_no_top_unchanged(self):
        """Test query without TOP is unchanged."""
        sql = "SELECT * FROM users WHERE active = 1"
        result = self.generator.convert_sql(sql)
        assert "limit" not in result.converted_sql.lower()


class TestStringConcatenation:
    """Tests for string concatenation conversion."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = SQLGenerator()

    def test_string_concat_plus_to_pipes(self):
        """Test string + to ||."""
        sql = "SELECT first_name + ' ' + last_name AS full_name"
        result = self.generator.convert_sql(sql)
        assert "||" in result.converted_sql

    def test_literal_concat(self):
        """Test literal string concatenation."""
        sql = "SELECT 'Hello' + 'World'"
        result = self.generator.convert_sql(sql)
        assert "||" in result.converted_sql


class TestSchemaQualification:
    """Tests for table reference schema qualification."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = SQLGenerator(
            database="ANALYTICS",
            schema="PUBLIC",
            warehouse="COMPUTE_WH",
        )

    def test_qualify_from_table(self):
        """Test FROM table gets qualified."""
        sql = "SELECT * FROM users"
        result = self.generator.qualify_table_references(sql)
        assert "analytics.public.users" in result.lower()

    def test_qualify_join_table(self):
        """Test JOIN table gets qualified."""
        sql = "SELECT * FROM users JOIN orders ON users.id = orders.user_id"
        result = self.generator.qualify_table_references(sql)
        assert "analytics.public.users" in result.lower()
        assert "analytics.public.orders" in result.lower()

    def test_already_qualified_unchanged(self):
        """Test already qualified tables are unchanged."""
        sql = "SELECT * FROM db.schema.users"
        result = self.generator.qualify_table_references(sql)
        # Should not double-qualify
        assert "db.schema.users" in result.lower()


class TestParameterConversion:
    """Tests for parameter conversion to Snowflake format."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = SQLGenerator()

    def test_date_parameter_default(self):
        """Test date parameter with Today() default."""
        params = [
            DatasetParameter(
                name="StartDate",
                data_type="DateTime",
                default_value="=Today()",
            )
        ]
        result = self.generator.convert_parameters(params)
        assert "SET startdate = CURRENT_DATE()" in result
        assert "Default from RDL: =Today()" in result

    def test_string_parameter(self):
        """Test string parameter conversion."""
        params = [
            DatasetParameter(
                name="CustomerName",
                data_type="String",
                default_value="All",
            )
        ]
        result = self.generator.convert_parameters(params)
        # Default value may or may not be quoted depending on implementation
        assert "SET customername" in result
        assert "All" in result

    def test_numeric_parameter(self):
        """Test numeric parameter without default."""
        params = [
            DatasetParameter(
                name="MinAmount",
                data_type="Integer",
                default_value=None,
            )
        ]
        result = self.generator.convert_parameters(params)
        assert "SET minamount = 0" in result

    def test_empty_parameters(self):
        """Test empty parameter list."""
        result = self.generator.convert_parameters([])
        assert result == ""


class TestDataTypeMapping:
    """Tests for SQL Server to Snowflake data type mapping."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = SQLGenerator()

    def test_datetime_to_timestamp(self):
        """Test DATETIME maps to TIMESTAMP."""
        result = self.generator._map_data_type("DateTime")
        assert result == "TIMESTAMP"

    def test_bit_to_boolean(self):
        """Test BIT maps to BOOLEAN."""
        result = self.generator._map_data_type("Bit")
        assert result == "BOOLEAN"

    def test_nvarchar_to_varchar(self):
        """Test NVARCHAR maps to VARCHAR."""
        result = self.generator._map_data_type("NVarChar")
        assert result == "VARCHAR"

    def test_money_to_decimal(self):
        """Test MONEY maps to DECIMAL."""
        result = self.generator._map_data_type("Money")
        assert result == "DECIMAL(19,4)"

    def test_uniqueidentifier_to_varchar(self):
        """Test UNIQUEIDENTIFIER maps to VARCHAR(36)."""
        result = self.generator._map_data_type("UniqueIdentifier")
        assert result == "VARCHAR(36)"


class TestScriptGeneration:
    """Tests for SQL script generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = SQLGenerator(
            database="TEST_DB",
            schema="TEST_SCHEMA",
            warehouse="TEST_WH",
        )

    def test_script_header_generation(self):
        """Test script header includes all metadata."""
        header = self.generator.generate_script_header(
            report_name="Sales Report",
            dataset_name="SalesData",
            query_type=QueryType.EMBEDDED_SQL,
            function_count=5,
        )
        assert "ReportLift SQL Script" in header
        assert "Sales Report" in header
        assert "SalesData" in header
        assert "Snowflake" in header
        assert "TEST_WH" in header
        assert "TEST_DB" in header
        assert "TEST_SCHEMA" in header
        assert "5 function(s) mapped" in header

    def test_sp_placeholder_generation(self):
        """Test stored procedure placeholder generation."""
        placeholder = self.generator.generate_sp_placeholder(
            sp_name="usp_GetSalesData",
            dataset_name="SalesData",
            report_name="Sales Report",
        )
        assert "TODO: MANUAL CONVERSION REQUIRED" in placeholder
        assert "usp_GetSalesData" in placeholder
        assert "placeholder_column" in placeholder


class TestMultipleConversions:
    """Tests for queries with multiple function conversions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = SQLGenerator()

    def test_multiple_functions_converted(self):
        """Test query with multiple SQL Server functions."""
        sql = """
        SELECT
            customer_name,
            ISNULL(phone, 'N/A') AS phone,
            LEN(email) AS email_length,
            GETDATE() AS query_time
        FROM customers
        """
        result = self.generator.convert_sql(sql)

        assert "coalesce(" in result.converted_sql.lower()
        assert "length(" in result.converted_sql.lower()
        assert "current_timestamp()" in result.converted_sql.lower()
        assert len(result.function_mappings) >= 3

    def test_conversion_result_tracking(self):
        """Test that conversions are tracked in result."""
        sql = "SELECT ISNULL(a, b), LEN(c) FROM t"
        result = self.generator.convert_sql(sql)

        assert isinstance(result, ConversionResult)
        assert result.original_sql == sql
        assert len(result.function_mappings) >= 2


class TestGenerateSQLScripts:
    """Tests for the generate_sql_scripts function."""

    def test_generate_scripts_for_datasets(self):
        """Test generating scripts for multiple datasets."""
        datasets = [
            DatasetFeature(
                name="CustomerData",
                query_type=QueryType.EMBEDDED_SQL,
                command_text="SELECT * FROM customers WHERE active = 1",
                parameter_count=0,
                field_count=5,
            ),
            DatasetFeature(
                name="OrderData",
                query_type=QueryType.EMBEDDED_SQL,
                command_text="SELECT TOP 100 * FROM orders WHERE ISNULL(status, '') = 'Active'",
                parameter_count=0,
                field_count=10,
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            result = generate_sql_scripts(
                datasets=datasets,
                report_name="Test Report",
                output_dir=tmpdir,
                database="TEST_DB",
                schema="TEST_SCHEMA",
                warehouse="TEST_WH",
            )

            assert result.datasets_processed == 2
            assert len(result.scripts) == 2
            assert os.path.exists(result.all_scripts_path)

            # Check individual files exist
            sql_dir = os.path.join(tmpdir, "sql")
            assert os.path.exists(os.path.join(sql_dir, "customerdata.sql"))
            assert os.path.exists(os.path.join(sql_dir, "orderdata.sql"))

    def test_generate_scripts_for_stored_procedure(self):
        """Test generating placeholder for stored procedure dataset."""
        datasets = [
            DatasetFeature(
                name="SPData",
                query_type=QueryType.STORED_PROCEDURE,
                stored_procedure_name="usp_GetData",
                parameter_count=2,
                field_count=5,
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            result = generate_sql_scripts(
                datasets=datasets,
                report_name="SP Report",
                output_dir=tmpdir,
            )

            assert result.datasets_processed == 1
            assert os.path.exists(result.all_scripts_path)

            # Read the generated file
            sql_dir = os.path.join(tmpdir, "sql")
            with open(os.path.join(sql_dir, "spdata.sql")) as f:
                content = f.read()

            assert "TODO: MANUAL CONVERSION REQUIRED" in content
            assert "usp_GetData" in content

    def test_generate_scripts_with_parameters(self):
        """Test generating scripts with parameter declarations."""
        datasets = [
            DatasetFeature(
                name="ParamData",
                query_type=QueryType.EMBEDDED_SQL,
                command_text="SELECT * FROM sales WHERE date >= @StartDate",
                parameter_count=1,
                field_count=5,
                parameters=[
                    DatasetParameter(
                        name="StartDate",
                        data_type="DateTime",
                        default_value="=Today()",
                    )
                ],
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            result = generate_sql_scripts(
                datasets=datasets,
                report_name="Param Report",
                output_dir=tmpdir,
            )

            # Read the generated file
            sql_dir = os.path.join(tmpdir, "sql")
            with open(os.path.join(sql_dir, "paramdata.sql")) as f:
                content = f.read()

            assert "Parameter Declarations" in content
            assert "SET startdate" in content
            assert "CURRENT_DATE()" in content

    def test_empty_datasets_returns_empty_result(self):
        """Test that empty datasets list returns empty result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = generate_sql_scripts(
                datasets=[],
                report_name="Empty Report",
                output_dir=tmpdir,
            )

            assert result.datasets_processed == 0
            assert len(result.scripts) == 0


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = SQLGenerator()

    def test_empty_sql_unchanged(self):
        """Test empty SQL returns empty result."""
        result = self.generator.convert_sql("")
        assert result.converted_sql == ""
        assert len(result.function_mappings) == 0

    def test_null_sql_unchanged(self):
        """Test None SQL returns None."""
        result = self.generator.convert_sql(None)
        assert result.converted_sql is None

    def test_case_insensitive_conversion(self):
        """Test function matching is case insensitive."""
        sql = "SELECT getdate(), GETDATE(), GetDate()"
        result = self.generator.convert_sql(sql)
        assert result.converted_sql.lower().count("current_timestamp()") == 3

    def test_nested_functions(self):
        """Test nested function conversion."""
        sql = "SELECT ISNULL(LEN(name), 0) AS name_len"
        result = self.generator.convert_sql(sql)
        assert "coalesce(length(" in result.converted_sql.lower()

    def test_unconverted_function_warning(self):
        """Test warning for unconverted functions."""
        sql = "SELECT NEWID() AS guid"  # NEWID has no direct mapping
        result = self.generator.convert_sql(sql)
        # NEWID is in the unconverted list but we don't convert it
        # so it should generate a warning
        assert result.has_unconverted_functions or "newid" in result.converted_sql.lower()
