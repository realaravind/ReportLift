"""Tests for the RDL Parser Service."""

import pytest

from app.schemas.analysis import (
    AnalysisFeatures,
    ExpressionCategory,
    QueryType,
    RDLParseError,
    VisualType,
)
from app.services.rdl_parser import RDLParser, parse_rdl


# Sample RDL content for testing
SIMPLE_RDL = """<?xml version="1.0" encoding="utf-8"?>
<Report xmlns="http://schemas.microsoft.com/sqlserver/reporting/2016/01/reportdefinition" xmlns:rd="http://schemas.microsoft.com/SQLServer/reporting/reportdesigner">
  <Description>Test Report</Description>
  <Author>Test Author</Author>
  <DataSources>
    <DataSource Name="TestDataSource">
      <ConnectionProperties>
        <DataProvider>SQL</DataProvider>
        <ConnectString>Data Source=server;Initial Catalog=db</ConnectString>
      </ConnectionProperties>
    </DataSource>
  </DataSources>
  <DataSets>
    <DataSet Name="TestDataset">
      <Query>
        <DataSourceName>TestDataSource</DataSourceName>
        <CommandText>SELECT * FROM TestTable</CommandText>
      </Query>
      <Fields>
        <Field Name="ID">
          <DataField>ID</DataField>
          <TypeName>System.Int32</TypeName>
        </Field>
        <Field Name="Name">
          <DataField>Name</DataField>
          <TypeName>System.String</TypeName>
        </Field>
      </Fields>
    </DataSet>
  </DataSets>
  <ReportParameters>
    <ReportParameter Name="StartDate">
      <DataType>DateTime</DataType>
    </ReportParameter>
  </ReportParameters>
  <Page>
    <PageHeight>11in</PageHeight>
    <PageWidth>8.5in</PageWidth>
    <LeftMargin>1in</LeftMargin>
    <RightMargin>1in</RightMargin>
    <TopMargin>1in</TopMargin>
    <BottomMargin>1in</BottomMargin>
  </Page>
  <Body>
    <ReportItems>
      <Tablix Name="SalesTable">
        <DataSetName>TestDataset</DataSetName>
        <TablixBody>
          <TablixColumns>
            <TablixColumn><Width>1in</Width></TablixColumn>
          </TablixColumns>
          <TablixRows>
            <TablixRow><Height>0.25in</Height></TablixRow>
          </TablixRows>
        </TablixBody>
        <TablixRowHierarchy>
          <TablixMembers>
            <TablixMember>
              <Group Name="RowGroup1">
                <GroupExpressions>
                  <GroupExpression>=Fields!ID.Value</GroupExpression>
                </GroupExpressions>
              </Group>
            </TablixMember>
          </TablixMembers>
        </TablixRowHierarchy>
      </Tablix>
      <Textbox Name="txtTotal">
        <Value>=Sum(Fields!Amount.Value)</Value>
      </Textbox>
    </ReportItems>
  </Body>
</Report>
"""

RDL_WITH_SP = """<?xml version="1.0" encoding="utf-8"?>
<Report xmlns="http://schemas.microsoft.com/sqlserver/reporting/2016/01/reportdefinition">
  <DataSets>
    <DataSet Name="SPDataset">
      <Query>
        <DataSourceName>MainDB</DataSourceName>
        <CommandType>StoredProcedure</CommandType>
        <CommandText>usp_GetSalesData</CommandText>
        <QueryParameters>
          <QueryParameter Name="@StartDate">
            <Value>=Parameters!StartDate.Value</Value>
          </QueryParameter>
        </QueryParameters>
      </Query>
      <Fields>
        <Field Name="SalesAmount"><DataField>SalesAmount</DataField></Field>
      </Fields>
    </DataSet>
    <DataSet Name="ExecDataset">
      <Query>
        <DataSourceName>MainDB</DataSourceName>
        <CommandText>EXEC usp_GetCustomers @Region = 'North'</CommandText>
      </Query>
    </DataSet>
  </DataSets>
</Report>
"""

RDL_WITH_CUSTOM_CODE = """<?xml version="1.0" encoding="utf-8"?>
<Report xmlns="http://schemas.microsoft.com/sqlserver/reporting/2016/01/reportdefinition">
  <Code>
Public Function FormatCurrency(ByVal value As Decimal) As String
    Return String.Format("{0:C}", value)
End Function

Private Function CalculateDiscount(ByVal price As Decimal, ByVal rate As Decimal) As Decimal
    Return price * rate
End Function
  </Code>
  <Body>
    <ReportItems>
      <Textbox Name="txtFormatted">
        <Value>=Code.FormatCurrency(Fields!Amount.Value)</Value>
      </Textbox>
    </ReportItems>
  </Body>
</Report>
"""

RDL_WITH_EXPRESSIONS = """<?xml version="1.0" encoding="utf-8"?>
<Report xmlns="http://schemas.microsoft.com/sqlserver/reporting/2016/01/reportdefinition">
  <Body>
    <ReportItems>
      <Textbox Name="txt1"><Value>=Fields!Name.Value</Value></Textbox>
      <Textbox Name="txt2"><Value>=Sum(Fields!Amount.Value)</Value></Textbox>
      <Textbox Name="txt3"><Value>=RunningValue(Fields!Sales.Value, Sum, Nothing)</Value></Textbox>
      <Textbox Name="txt4"><Value>=Lookup(Fields!ID.Value, Fields!ID.Value, Fields!Name.Value, "Dataset2")</Value></Textbox>
      <Textbox Name="txt5"><Value>=RowNumber(Nothing)</Value></Textbox>
      <Textbox Name="txt6"><Value>=Previous(Fields!Amount.Value)</Value></Textbox>
      <Textbox Name="txt7"><Value>=Sum(Fields!Amount.Value, "GroupName", "All")</Value></Textbox>
    </ReportItems>
  </Body>
</Report>
"""

RDL_WITH_COMPLEX_VISUALS = """<?xml version="1.0" encoding="utf-8"?>
<Report xmlns="http://schemas.microsoft.com/sqlserver/reporting/2016/01/reportdefinition">
  <Body>
    <ReportItems>
      <Chart Name="SalesChart">
        <DataSetName>SalesData</DataSetName>
      </Chart>
      <Gauge Name="KPIGauge">
        <GaugePanel></GaugePanel>
      </Gauge>
      <Map Name="RegionMap">
        <MapViewport></MapViewport>
      </Map>
      <Subreport Name="DetailReport">
        <ReportName>/Reports/DetailReport</ReportName>
      </Subreport>
      <Rectangle Name="Container">
        <ReportItems>
          <Textbox Name="Inner1"><Value>Text</Value></Textbox>
          <Textbox Name="Inner2"><Value>Text</Value></Textbox>
        </ReportItems>
      </Rectangle>
    </ReportItems>
  </Body>
</Report>
"""

RDL_WITH_RECURSIVE_GROUP = """<?xml version="1.0" encoding="utf-8"?>
<Report xmlns="http://schemas.microsoft.com/sqlserver/reporting/2016/01/reportdefinition">
  <Body>
    <ReportItems>
      <Tablix Name="OrgChart">
        <TablixRowHierarchy>
          <TablixMembers>
            <TablixMember>
              <Group Name="EmployeeGroup">
                <GroupExpressions>
                  <GroupExpression>=Fields!EmployeeID.Value</GroupExpression>
                </GroupExpressions>
                <Parent>=Fields!ManagerID.Value</Parent>
              </Group>
            </TablixMember>
          </TablixMembers>
        </TablixRowHierarchy>
      </Tablix>
    </ReportItems>
  </Body>
</Report>
"""


class TestRDLNamespaceDetection:
    """Test namespace detection for different RDL versions."""

    def test_detects_2016_namespace(self):
        parser = RDLParser(SIMPLE_RDL)
        assert parser.version == "2016"
        assert "2016" in parser.namespace

    def test_detects_2010_namespace(self):
        rdl_2010 = SIMPLE_RDL.replace(
            "http://schemas.microsoft.com/sqlserver/reporting/2016/01/reportdefinition",
            "http://schemas.microsoft.com/sqlserver/reporting/2010/01/reportdefinition",
        )
        parser = RDLParser(rdl_2010)
        assert parser.version == "2010"

    def test_detects_2008_namespace(self):
        rdl_2008 = SIMPLE_RDL.replace(
            "http://schemas.microsoft.com/sqlserver/reporting/2016/01/reportdefinition",
            "http://schemas.microsoft.com/sqlserver/reporting/2008/01/reportdefinition",
        )
        parser = RDLParser(rdl_2008)
        assert parser.version == "2008"


class TestRDLParseError:
    """Test error handling for invalid RDL content."""

    def test_invalid_xml_raises_error(self):
        with pytest.raises(RDLParseError) as exc_info:
            RDLParser("<not>valid<xml>")
        assert "Invalid RDL XML format" in str(exc_info.value)

    def test_empty_content_raises_error(self):
        with pytest.raises(RDLParseError):
            RDLParser("")

    def test_non_rdl_xml_raises_error(self):
        with pytest.raises(RDLParseError) as exc_info:
            RDLParser("<root><child>text</child></root>")
        assert "namespace" in str(exc_info.value).lower()


class TestDatasetExtraction:
    """Test dataset feature extraction."""

    def test_extracts_basic_dataset(self):
        features = parse_rdl(SIMPLE_RDL)
        assert features.dataset_count == 1
        assert len(features.datasets) == 1

        ds = features.datasets[0]
        assert ds.name == "TestDataset"
        assert ds.query_type == QueryType.EMBEDDED_SQL
        assert ds.data_source_name == "TestDataSource"
        assert ds.field_count == 2

    def test_extracts_stored_procedure_dataset(self):
        features = parse_rdl(RDL_WITH_SP)
        assert features.dataset_count == 2
        assert features.stored_procedure_count == 2
        assert features.has_stored_procedures is True

        # First dataset uses CommandType=StoredProcedure
        ds1 = features.datasets[0]
        assert ds1.query_type == QueryType.STORED_PROCEDURE
        assert ds1.stored_procedure_name == "usp_GetSalesData"
        assert ds1.parameter_count == 1

        # Second dataset uses EXEC
        ds2 = features.datasets[1]
        assert ds2.query_type == QueryType.STORED_PROCEDURE
        assert "usp_GetCustomers" in (ds2.stored_procedure_name or "")

    def test_extracts_dataset_fields(self):
        features = parse_rdl(SIMPLE_RDL)
        ds = features.datasets[0]

        assert len(ds.fields) == 2
        assert ds.fields[0].name == "ID"
        assert ds.fields[0].data_type == "System.Int32"
        assert ds.fields[1].name == "Name"


class TestVisualExtraction:
    """Test visual element extraction."""

    def test_extracts_tablix(self):
        features = parse_rdl(SIMPLE_RDL)
        tablixes = [v for v in features.visuals if v.type == VisualType.TABLIX]
        assert len(tablixes) == 1
        assert tablixes[0].name == "SalesTable"
        assert tablixes[0].dataset_name == "TestDataset"
        assert tablixes[0].row_groups == 1

    def test_extracts_charts_gauges_maps(self):
        features = parse_rdl(RDL_WITH_COMPLEX_VISUALS)
        assert features.chart_count == 1
        assert features.gauge_count == 1
        assert features.map_count == 1

    def test_extracts_subreports(self):
        features = parse_rdl(RDL_WITH_COMPLEX_VISUALS)
        assert features.subreport_count == 1
        assert features.has_subreports is True

        subreports = [v for v in features.visuals if v.type == VisualType.SUBREPORT]
        assert len(subreports) == 1
        assert subreports[0].subreport_path == "/Reports/DetailReport"

    def test_extracts_nested_items_in_rectangle(self):
        features = parse_rdl(RDL_WITH_COMPLEX_VISUALS)
        rectangles = [v for v in features.visuals if v.type == VisualType.RECTANGLE]
        assert len(rectangles) == 1
        assert rectangles[0].nested_item_count == 2

    def test_detects_recursive_groups(self):
        features = parse_rdl(RDL_WITH_RECURSIVE_GROUP)
        assert features.has_recursive_groups is True

        tablixes = [v for v in features.visuals if v.type == VisualType.TABLIX]
        assert len(tablixes) == 1
        assert tablixes[0].has_recursive_group is True


class TestExpressionExtraction:
    """Test expression feature extraction."""

    def test_categorizes_field_reference(self):
        features = parse_rdl(RDL_WITH_EXPRESSIONS)
        field_refs = [
            e for e in features.expressions
            if e.category == ExpressionCategory.FIELD_REFERENCE
        ]
        assert len(field_refs) >= 1

    def test_categorizes_simple_aggregate(self):
        features = parse_rdl(RDL_WITH_EXPRESSIONS)
        aggregates = [
            e for e in features.expressions
            if e.category == ExpressionCategory.SIMPLE_AGGREGATE
        ]
        assert len(aggregates) >= 1

    def test_categorizes_running_value(self):
        features = parse_rdl(RDL_WITH_EXPRESSIONS)
        assert features.running_value_count >= 1
        assert features.has_running_values is True

        running_vals = [
            e for e in features.expressions
            if e.category == ExpressionCategory.RUNNING_VALUE
        ]
        assert len(running_vals) >= 1

    def test_categorizes_lookup(self):
        features = parse_rdl(RDL_WITH_EXPRESSIONS)
        assert features.has_lookup_expressions is True

        lookups = [
            e for e in features.expressions
            if e.category == ExpressionCategory.LOOKUP
        ]
        assert len(lookups) >= 1

    def test_categorizes_row_number(self):
        features = parse_rdl(RDL_WITH_EXPRESSIONS)
        row_nums = [
            e for e in features.expressions
            if e.category == ExpressionCategory.ROW_NUMBER
        ]
        assert len(row_nums) >= 1

    def test_categorizes_custom_code_call(self):
        features = parse_rdl(RDL_WITH_CUSTOM_CODE)
        code_calls = [
            e for e in features.expressions
            if e.category == ExpressionCategory.CUSTOM_CODE
        ]
        assert len(code_calls) >= 1


class TestCustomCodeExtraction:
    """Test custom VB.NET code extraction."""

    def test_extracts_custom_code(self):
        features = parse_rdl(RDL_WITH_CUSTOM_CODE)
        assert features.has_custom_code is True
        assert features.custom_code is not None
        assert "FormatCurrency" in features.custom_code

    def test_extracts_function_names(self):
        features = parse_rdl(RDL_WITH_CUSTOM_CODE)
        assert features.custom_code_function_count == 2

        func_names = [f.name for f in features.custom_code_functions]
        assert "FormatCurrency" in func_names
        assert "CalculateDiscount" in func_names

    def test_extracts_function_parameters(self):
        features = parse_rdl(RDL_WITH_CUSTOM_CODE)
        format_func = next(
            f for f in features.custom_code_functions
            if f.name == "FormatCurrency"
        )
        assert len(format_func.parameters) == 1

        calc_func = next(
            f for f in features.custom_code_functions
            if f.name == "CalculateDiscount"
        )
        assert len(calc_func.parameters) == 2


class TestLayoutExtraction:
    """Test layout feature extraction."""

    def test_extracts_page_dimensions(self):
        features = parse_rdl(SIMPLE_RDL)
        layout = features.layout
        assert layout is not None
        assert layout.page_width == "8.5in"
        assert layout.page_height == "11in"
        assert layout.page_width_inches == 8.5
        assert layout.page_height_inches == 11.0

    def test_detects_orientation(self):
        features = parse_rdl(SIMPLE_RDL)
        assert features.layout.orientation == "Portrait"

        # Create landscape RDL
        landscape_rdl = SIMPLE_RDL.replace(
            "<PageWidth>8.5in</PageWidth>",
            "<PageWidth>11in</PageWidth>",
        ).replace(
            "<PageHeight>11in</PageHeight>",
            "<PageHeight>8.5in</PageHeight>",
        )
        features = parse_rdl(landscape_rdl)
        assert features.layout.orientation == "Landscape"

    def test_extracts_margins(self):
        features = parse_rdl(SIMPLE_RDL)
        layout = features.layout
        assert layout.left_margin == "1in"
        assert layout.right_margin == "1in"
        assert layout.top_margin == "1in"
        assert layout.bottom_margin == "1in"


class TestReportParameterExtraction:
    """Test report parameter extraction."""

    def test_extracts_report_parameters(self):
        features = parse_rdl(SIMPLE_RDL)
        assert features.parameter_count == 1
        assert len(features.report_parameters) == 1

        param = features.report_parameters[0]
        assert param.name == "StartDate"
        assert param.data_type == "DateTime"


class TestDataSourceExtraction:
    """Test data source extraction."""

    def test_extracts_data_sources(self):
        features = parse_rdl(SIMPLE_RDL)
        assert len(features.data_sources) == 1
        assert "TestDataSource" in features.data_sources


class TestLegacyDictConversion:
    """Test conversion to legacy dict format."""

    def test_converts_to_legacy_dict(self):
        features = parse_rdl(SIMPLE_RDL)
        legacy = features.to_legacy_dict()

        assert legacy["datasets"] == 1
        assert legacy["data_sources"] == 1
        assert legacy["parameters"] == 1
        assert legacy["tables"] == 1
        assert isinstance(legacy["custom_code"], bool)
        assert isinstance(legacy["has_grouping"], bool)


class TestParseRdlFunction:
    """Test the convenience parse_rdl function."""

    def test_parses_rdl_successfully(self):
        features = parse_rdl(SIMPLE_RDL)
        assert isinstance(features, AnalysisFeatures)
        assert features.rdl_version == "2016"

    def test_handles_bytes_input(self):
        features = parse_rdl(SIMPLE_RDL.encode("utf-8"))
        assert isinstance(features, AnalysisFeatures)

    def test_handles_bom(self):
        # Add UTF-8 BOM
        rdl_with_bom = b"\xef\xbb\xbf" + SIMPLE_RDL.encode("utf-8")
        features = parse_rdl(rdl_with_bom)
        assert isinstance(features, AnalysisFeatures)
