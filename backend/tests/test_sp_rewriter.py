"""Tests for Stored Procedure Rewriter service."""

import pytest

from app.services.sp_rewriter import (
    SPParser,
    SPClassifier,
    SPRewriter,
    SPClassification,
    ConfidenceLevel,
    SPParameter,
    ComplexityElement,
    classify_stored_procedure,
    rewrite_stored_procedure,
)


class TestSPParser:
    """Tests for SPParser complexity detection."""

    def test_detect_temp_tables_hash(self):
        """Test detection of #temp tables."""
        sp = """
        CREATE PROCEDURE GetData
        AS
        BEGIN
            SELECT * INTO #TempResults FROM Sales
            SELECT * FROM #TempResults
        END
        """
        parser = SPParser(sp)
        elements = parser.detect_temp_tables()
        assert len(elements) > 0
        assert any("temp_table" in e.element_type for e in elements)

    def test_detect_table_variables(self):
        """Test detection of @table variables."""
        sp = """
        CREATE PROCEDURE GetData
        AS
        BEGIN
            DECLARE @Results TABLE (ID INT, Name VARCHAR(100))
            INSERT INTO @Results SELECT ID, Name FROM Sales
            SELECT * FROM @Results
        END
        """
        parser = SPParser(sp)
        elements = parser.detect_temp_tables()
        assert len(elements) > 0

    def test_detect_cursors(self):
        """Test detection of cursor operations."""
        sp = """
        CREATE PROCEDURE ProcessOrders
        AS
        BEGIN
            DECLARE order_cursor CURSOR FOR SELECT OrderID FROM Orders
            OPEN order_cursor
            FETCH NEXT FROM order_cursor
            CLOSE order_cursor
            DEALLOCATE order_cursor
        END
        """
        parser = SPParser(sp)
        elements = parser.detect_cursors()
        assert len(elements) > 0
        assert any("cursor" in e.element_type for e in elements)

    def test_detect_dynamic_sql_exec(self):
        """Test detection of EXEC dynamic SQL."""
        sp = """
        CREATE PROCEDURE DynamicQuery
        AS
        BEGIN
            DECLARE @sql NVARCHAR(MAX)
            SET @sql = 'SELECT * FROM Orders'
            EXEC(@sql)
        END
        """
        parser = SPParser(sp)
        elements = parser.detect_dynamic_sql()
        assert len(elements) > 0
        assert any("dynamic_sql" in e.element_type for e in elements)

    def test_detect_dynamic_sql_executesql(self):
        """Test detection of sp_executesql."""
        sp = """
        CREATE PROCEDURE DynamicQuery
        AS
        BEGIN
            EXEC sp_executesql N'SELECT * FROM Orders WHERE ID = @id', N'@id INT', @id = 1
        END
        """
        parser = SPParser(sp)
        elements = parser.detect_dynamic_sql()
        assert len(elements) > 0

    def test_detect_transactions(self):
        """Test detection of transaction control."""
        sp = """
        CREATE PROCEDURE TransferFunds
        AS
        BEGIN
            BEGIN TRANSACTION
            UPDATE Accounts SET Balance = Balance - 100 WHERE ID = 1
            UPDATE Accounts SET Balance = Balance + 100 WHERE ID = 2
            COMMIT TRANSACTION
        END
        """
        parser = SPParser(sp)
        elements = parser.detect_transactions()
        assert len(elements) >= 2  # BEGIN TRAN and COMMIT

    def test_detect_rollback(self):
        """Test detection of ROLLBACK."""
        sp = """
        CREATE PROCEDURE SafeUpdate
        AS
        BEGIN
            BEGIN TRAN
            UPDATE Orders SET Status = 'Processed'
            IF @@ERROR <> 0 ROLLBACK TRAN
            ELSE COMMIT TRAN
        END
        """
        parser = SPParser(sp)
        elements = parser.detect_transactions()
        assert len(elements) >= 2

    def test_detect_while_loop(self):
        """Test detection of WHILE loops."""
        sp = """
        CREATE PROCEDURE BatchProcess
        AS
        BEGIN
            DECLARE @i INT = 0
            WHILE @i < 100
            BEGIN
                UPDATE Orders SET Processed = 1 WHERE ID = @i
                SET @i = @i + 1
            END
        END
        """
        parser = SPParser(sp)
        elements = parser.detect_control_flow()
        assert len(elements) > 0
        assert any("control_flow" in e.element_type for e in elements)

    def test_detect_goto(self):
        """Test detection of GOTO statements."""
        sp = """
        CREATE PROCEDURE CheckData
        AS
        BEGIN
            IF @value < 0 GOTO ErrorHandler
            SELECT * FROM Data
            RETURN
            ErrorHandler:
            RAISERROR('Invalid value', 16, 1)
        END
        """
        parser = SPParser(sp)
        elements = parser.detect_control_flow()
        assert len(elements) > 0

    def test_count_select_statements_single(self):
        """Test counting single SELECT."""
        sp = "SELECT * FROM Orders WHERE Status = 'Active'"
        parser = SPParser(sp)
        assert parser.count_select_statements() == 1

    def test_count_select_statements_multiple(self):
        """Test counting multiple SELECTs."""
        sp = """
        CREATE PROCEDURE GetData
        AS
        BEGIN
            SELECT * FROM Orders
            SELECT * FROM Customers
            SELECT * FROM Products
        END
        """
        parser = SPParser(sp)
        assert parser.count_select_statements() == 3

    def test_has_union(self):
        """Test UNION detection."""
        sp = """
        SELECT ID, Name FROM Customers
        UNION ALL
        SELECT ID, Name FROM Vendors
        """
        parser = SPParser(sp)
        assert parser.has_union() is True

    def test_no_union(self):
        """Test no UNION case."""
        sp = "SELECT * FROM Orders"
        parser = SPParser(sp)
        assert parser.has_union() is False

    def test_count_if_else(self):
        """Test IF statement counting."""
        sp = """
        CREATE PROCEDURE CheckData
        AS
        BEGIN
            IF @status = 1
                SELECT * FROM Active
            ELSE IF @status = 2
                SELECT * FROM Inactive
            ELSE
                SELECT * FROM All
        END
        """
        parser = SPParser(sp)
        assert parser.count_if_else() >= 2

    def test_no_complexity_elements(self):
        """Test simple SP has no complexity elements."""
        sp = """
        CREATE PROCEDURE GetSales
            @StartDate DATE
        AS
        BEGIN
            SET NOCOUNT ON
            SELECT CustomerName, SUM(Amount)
            FROM Sales
            WHERE SaleDate >= @StartDate
            GROUP BY CustomerName
        END
        """
        parser = SPParser(sp)
        elements = parser.get_all_complexity_elements()
        assert len(elements) == 0


class TestSPClassifier:
    """Tests for SPClassifier classification."""

    def test_classify_simple_sp(self):
        """Test classification of simple SP."""
        sp = """
        CREATE PROCEDURE GetSalesByDate
            @StartDate DATE,
            @EndDate DATE
        AS
        BEGIN
            SELECT
                CustomerName,
                SUM(SalesAmount) as TotalSales
            FROM Sales
            WHERE SaleDate BETWEEN @StartDate AND @EndDate
            GROUP BY CustomerName
        END
        """
        parser = SPParser(sp)
        classifier = SPClassifier(parser)
        result = classifier.classify()
        assert result.classification == SPClassification.SIMPLE
        assert len(result.complexity_elements) == 0

    def test_classify_moderate_sp_with_union(self):
        """Test classification of SP with UNION."""
        sp = """
        CREATE PROCEDURE GetAllContacts
        AS
        BEGIN
            SELECT ID, Name, 'Customer' AS Type FROM Customers
            UNION ALL
            SELECT ID, Name, 'Vendor' AS Type FROM Vendors
        END
        """
        parser = SPParser(sp)
        classifier = SPClassifier(parser)
        result = classifier.classify()
        assert result.classification == SPClassification.MODERATE
        assert result.has_union is True

    def test_classify_moderate_sp_with_simple_if(self):
        """Test classification of SP with simple IF."""
        sp = """
        CREATE PROCEDURE GetData
            @type INT
        AS
        BEGIN
            IF @type = 1
                SELECT * FROM TypeA
            ELSE
                SELECT * FROM TypeB
        END
        """
        parser = SPParser(sp)
        classifier = SPClassifier(parser)
        result = classifier.classify()
        assert result.classification == SPClassification.MODERATE

    def test_classify_complex_sp_with_temp_table(self):
        """Test classification of SP with temp table."""
        sp = """
        CREATE PROCEDURE ProcessData
        AS
        BEGIN
            SELECT * INTO #TempData FROM Source
            UPDATE #TempData SET Flag = 1
            SELECT * FROM #TempData
        END
        """
        parser = SPParser(sp)
        classifier = SPClassifier(parser)
        result = classifier.classify()
        assert result.classification == SPClassification.COMPLEX
        assert len(result.complexity_elements) > 0

    def test_classify_complex_sp_with_cursor(self):
        """Test classification of SP with cursor."""
        sp = """
        CREATE PROCEDURE IterateOrders
        AS
        BEGIN
            DECLARE cur CURSOR FOR SELECT ID FROM Orders
            OPEN cur
            FETCH NEXT FROM cur
        END
        """
        parser = SPParser(sp)
        classifier = SPClassifier(parser)
        result = classifier.classify()
        assert result.classification == SPClassification.COMPLEX

    def test_classify_complex_sp_with_dynamic_sql(self):
        """Test classification of SP with dynamic SQL."""
        sp = """
        CREATE PROCEDURE DynamicReport
            @tableName VARCHAR(100)
        AS
        BEGIN
            EXEC('SELECT * FROM ' + @tableName)
        END
        """
        parser = SPParser(sp)
        classifier = SPClassifier(parser)
        result = classifier.classify()
        assert result.classification == SPClassification.COMPLEX

    def test_classify_complex_sp_with_transaction(self):
        """Test classification of SP with transaction."""
        sp = """
        CREATE PROCEDURE TransferMoney
        AS
        BEGIN
            BEGIN TRANSACTION
            UPDATE Account1 SET Balance = Balance - 100
            UPDATE Account2 SET Balance = Balance + 100
            COMMIT TRANSACTION
        END
        """
        parser = SPParser(sp)
        classifier = SPClassifier(parser)
        result = classifier.classify()
        assert result.classification == SPClassification.COMPLEX

    def test_classify_complex_sp_with_while(self):
        """Test classification of SP with WHILE loop."""
        sp = """
        CREATE PROCEDURE BatchUpdate
        AS
        BEGIN
            DECLARE @i INT = 0
            WHILE @i < 100
            BEGIN
                UPDATE Data SET Processed = 1 WHERE ID = @i
                SET @i = @i + 1
            END
        END
        """
        parser = SPParser(sp)
        classifier = SPClassifier(parser)
        result = classifier.classify()
        assert result.classification == SPClassification.COMPLEX


class TestSPRewriter:
    """Tests for SPRewriter rewrite functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.rewriter = SPRewriter(
            database="TEST_DB",
            schema="TEST_SCHEMA",
            warehouse="TEST_WH",
        )

    def test_rewrite_simple_sp(self):
        """Test rewriting a simple stored procedure."""
        sp = """
        CREATE PROCEDURE GetSales
            @StartDate DATE
        AS
        BEGIN
            SET NOCOUNT ON
            SELECT CustomerName, SUM(Amount) AS TotalAmount
            FROM Sales
            WHERE SaleDate >= @StartDate
            GROUP BY CustomerName
        END
        """
        result = self.rewriter.rewrite(
            sp_name="GetSales",
            sp_definition=sp,
        )
        assert result.success is True
        assert result.classification == SPClassification.SIMPLE
        assert result.confidence == ConfidenceLevel.HIGH
        assert result.converted_sql is not None
        assert "$startdate" in result.converted_sql.lower()
        assert "test_db.test_schema" in result.converted_sql.lower()

    def test_rewrite_simple_sp_with_multiple_params(self):
        """Test rewriting SP with multiple parameters."""
        sp = """
        CREATE PROCEDURE GetOrders
            @CustomerID INT,
            @Status VARCHAR(20) = 'Active'
        AS
        BEGIN
            SELECT OrderID, OrderDate, Total
            FROM Orders
            WHERE CustomerID = @CustomerID AND Status = @Status
        END
        """
        result = self.rewriter.rewrite(
            sp_name="GetOrders",
            sp_definition=sp,
        )
        assert result.success is True
        assert len(result.parameters) == 2
        assert any(p.name == "CustomerID" for p in result.parameters)
        assert any(p.name == "Status" for p in result.parameters)

    def test_rewrite_moderate_sp_with_union(self):
        """Test rewriting moderate SP with UNION."""
        sp = """
        CREATE PROCEDURE GetAllPeople
        AS
        BEGIN
            SELECT ID, Name FROM Customers
            UNION ALL
            SELECT ID, Name FROM Employees
        END
        """
        result = self.rewriter.rewrite(
            sp_name="GetAllPeople",
            sp_definition=sp,
        )
        assert result.classification == SPClassification.MODERATE
        assert result.confidence == ConfidenceLevel.MEDIUM
        assert "union" in result.converted_sql.lower()

    def test_handle_complex_sp(self):
        """Test handling complex SP generates placeholder."""
        sp = """
        CREATE PROCEDURE ComplexProcess
        AS
        BEGIN
            SELECT * INTO #TempData FROM Source
            DECLARE cur CURSOR FOR SELECT ID FROM #TempData
            OPEN cur
            FETCH NEXT FROM cur
        END
        """
        result = self.rewriter.rewrite(
            sp_name="ComplexProcess",
            sp_definition=sp,
        )
        assert result.success is False
        assert result.classification == SPClassification.COMPLEX
        assert result.confidence == ConfidenceLevel.NA
        assert "TODO" in result.converted_sql
        assert "ComplexProcess" in result.converted_sql
        assert len(result.complexity_elements) > 0

    def test_handle_sp_without_definition(self):
        """Test handling SP without definition."""
        result = self.rewriter.rewrite(
            sp_name="UnknownSP",
            sp_definition=None,
            sp_call="EXEC UnknownSP @id = 1",
        )
        assert result.success is False
        assert result.confidence == ConfidenceLevel.NA
        assert "TODO" in result.converted_sql
        assert "UnknownSP" in result.converted_sql

    def test_validation_suggestions_high_confidence(self):
        """Test validation suggestions for HIGH confidence."""
        sp = """
        CREATE PROCEDURE SimpleQuery
        AS
        BEGIN
            SELECT * FROM Data
        END
        """
        result = self.rewriter.rewrite(
            sp_name="SimpleQuery",
            sp_definition=sp,
        )
        assert result.confidence == ConfidenceLevel.HIGH
        assert len(result.validation_suggestions) > 0
        assert any("row count" in s.lower() for s in result.validation_suggestions)

    def test_validation_suggestions_complex(self):
        """Test validation suggestions for COMPLEX SP."""
        sp = """
        CREATE PROCEDURE ComplexQuery
        AS
        BEGIN
            BEGIN TRANSACTION
            SELECT * FROM Data
            COMMIT
        END
        """
        result = self.rewriter.rewrite(
            sp_name="ComplexQuery",
            sp_definition=sp,
        )
        assert result.confidence == ConfidenceLevel.NA
        assert len(result.validation_suggestions) > 0
        assert any("manual" in s.lower() for s in result.validation_suggestions)

    def test_sql_function_conversion_in_sp(self):
        """Test SQL Server functions are converted in SP."""
        sp = """
        CREATE PROCEDURE GetRecentData
        AS
        BEGIN
            SELECT
                CustomerName,
                ISNULL(Phone, 'N/A') AS Phone,
                GETDATE() AS RetrievedAt
            FROM Customers
        END
        """
        result = self.rewriter.rewrite(
            sp_name="GetRecentData",
            sp_definition=sp,
        )
        assert result.success is True
        # Check functions were converted
        sql_lower = result.converted_sql.lower()
        assert "coalesce(" in sql_lower
        assert "current_timestamp()" in sql_lower
        assert "isnull(" not in sql_lower
        assert "getdate()" not in sql_lower


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_classify_stored_procedure(self):
        """Test classify_stored_procedure function."""
        sp = """
        CREATE PROCEDURE SimpleSelect AS
        BEGIN SELECT * FROM Data END
        """
        result = classify_stored_procedure(sp)
        assert result.classification == SPClassification.SIMPLE

    def test_rewrite_stored_procedure(self):
        """Test rewrite_stored_procedure function."""
        sp = """
        CREATE PROCEDURE GetData AS
        BEGIN SELECT * FROM Data END
        """
        result = rewrite_stored_procedure(
            sp_name="GetData",
            sp_definition=sp,
            database="MY_DB",
            schema="MY_SCHEMA",
            warehouse="MY_WH",
        )
        assert result.original_sp_name == "GetData"
        assert "MY_DB" in result.converted_sql
        assert "MY_SCHEMA" in result.converted_sql


class TestParameterExtraction:
    """Tests for parameter extraction from SP definitions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.rewriter = SPRewriter()

    def test_extract_single_parameter(self):
        """Test extracting single parameter."""
        sp = """
        CREATE PROCEDURE GetSales
            @StartDate DATE
        AS
        BEGIN
            SELECT * FROM Sales WHERE Date >= @StartDate
        END
        """
        params = self.rewriter._extract_sp_parameters(sp)
        assert len(params) == 1
        assert params[0].name == "StartDate"
        assert params[0].data_type == "DATE"

    def test_extract_multiple_parameters(self):
        """Test extracting multiple parameters."""
        sp = """
        CREATE PROCEDURE GetSales
            @StartDate DATE,
            @EndDate DATE,
            @CustomerID INT
        AS
        BEGIN
            SELECT * FROM Sales
        END
        """
        params = self.rewriter._extract_sp_parameters(sp)
        assert len(params) == 3
        param_names = [p.name for p in params]
        assert "StartDate" in param_names
        assert "EndDate" in param_names
        assert "CustomerID" in param_names

    def test_extract_parameter_with_default(self):
        """Test extracting parameter with default value."""
        sp = """
        CREATE PROCEDURE GetData
            @Status VARCHAR(20) = 'Active',
            @Limit INT = 100
        AS
        BEGIN
            SELECT TOP (@Limit) * FROM Data WHERE Status = @Status
        END
        """
        params = self.rewriter._extract_sp_parameters(sp)
        assert len(params) == 2

        status_param = next(p for p in params if p.name == "Status")
        assert status_param.default_value == "'Active'"

        limit_param = next(p for p in params if p.name == "Limit")
        assert limit_param.default_value == "100"

    def test_extract_typed_parameters(self):
        """Test extracting various typed parameters."""
        sp = """
        CREATE PROCEDURE TestTypes
            @IntVal INT,
            @VarcharVal VARCHAR(100),
            @DecimalVal DECIMAL(10,2),
            @DateVal DATETIME
        AS
        BEGIN
            SELECT 1
        END
        """
        params = self.rewriter._extract_sp_parameters(sp)
        assert len(params) == 4

        types = {p.name: p.data_type for p in params}
        assert types["IntVal"] == "INT"
        assert "VARCHAR" in types["VarcharVal"]
        assert "DECIMAL" in types["DecimalVal"]
        assert types["DateVal"] == "DATETIME"


class TestSelectExtraction:
    """Tests for SELECT statement extraction from SP body."""

    def setup_method(self):
        """Set up test fixtures."""
        self.rewriter = SPRewriter()

    def test_extract_simple_select(self):
        """Test extracting simple SELECT."""
        sp = """
        CREATE PROCEDURE GetData
        AS
        BEGIN
            SELECT * FROM Data
        END
        """
        select = self.rewriter._extract_select_statement(sp)
        assert select is not None
        assert "SELECT" in select.upper()
        assert "Data" in select

    def test_extract_select_with_set_nocount(self):
        """Test SET NOCOUNT ON is removed."""
        sp = """
        CREATE PROCEDURE GetData
        AS
        BEGIN
            SET NOCOUNT ON
            SELECT * FROM Data
        END
        """
        select = self.rewriter._extract_select_statement(sp)
        assert select is not None
        assert "NOCOUNT" not in select.upper()
        assert "SELECT" in select.upper()

    def test_extract_complex_select(self):
        """Test extracting complex SELECT with WHERE and GROUP BY."""
        sp = """
        CREATE PROCEDURE GetSales
        AS
        BEGIN
            SET NOCOUNT ON
            SELECT
                CustomerName,
                SUM(Amount) AS Total,
                COUNT(*) AS Orders
            FROM Sales
            WHERE Status = 'Complete'
            GROUP BY CustomerName
            HAVING SUM(Amount) > 1000
            ORDER BY Total DESC
        END
        """
        select = self.rewriter._extract_select_statement(sp)
        assert select is not None
        assert "SUM(Amount)" in select
        assert "GROUP BY" in select.upper()
        assert "HAVING" in select.upper()
        assert "ORDER BY" in select.upper()


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.rewriter = SPRewriter()

    def test_empty_sp_definition(self):
        """Test handling empty SP definition."""
        result = self.rewriter.rewrite(
            sp_name="EmptySP",
            sp_definition="",
        )
        # Empty definition should be treated as no definition
        assert result.success is False

    def test_malformed_sp(self):
        """Test handling malformed SP."""
        sp = "CREATE PROCEDURE Broken AS SELECT"
        result = self.rewriter.rewrite(
            sp_name="Broken",
            sp_definition=sp,
        )
        # Should still return a result, even if extraction fails
        assert result.original_sp_name == "Broken"

    def test_sp_with_comments(self):
        """Test SP with inline comments."""
        sp = """
        -- This is a comment
        CREATE PROCEDURE GetData
        AS
        BEGIN
            /* Multi-line
               comment */
            SELECT * FROM Data -- Inline comment
        END
        """
        result = self.rewriter.rewrite(
            sp_name="GetData",
            sp_definition=sp,
        )
        assert result.classification == SPClassification.SIMPLE

    def test_sp_with_special_characters(self):
        """Test SP with special characters in names."""
        sp = """
        CREATE PROCEDURE [dbo].[Get Sales Data]
            @StartDate DATE
        AS
        BEGIN
            SELECT * FROM [Sales Data] WHERE [Order Date] >= @StartDate
        END
        """
        result = self.rewriter.rewrite(
            sp_name="Get Sales Data",
            sp_definition=sp,
        )
        # Should still classify and attempt conversion
        assert result.original_sp_name == "Get Sales Data"

    def test_sp_only_call_no_definition(self):
        """Test SP with only call syntax, no definition."""
        result = self.rewriter.rewrite(
            sp_name="MissingSP",
            sp_definition=None,
            sp_call="EXEC MissingSP @param1 = 'value', @param2 = 123",
        )
        assert result.success is False
        assert "MissingSP" in result.converted_sql
        assert "EXEC MissingSP" in result.converted_sql
