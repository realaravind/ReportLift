# Story 5.4: Power BI Report Generation

Status: done

## Story

As a **user**,
I want **a Power BI report file (.pbix) generated from the SSRS report**,
so that **I have a converted report ready for Power BI Desktop**.

## Acceptance Criteria

### AC1: Valid PBIX Generation
**Given** analysis and SQL generation are complete
**When** generating the Power BI file
**Then** a valid .pbix file is created
**And** the file opens in Power BI Desktop without errors (NFR10)

### AC2: Table Visual Conversion
**Given** the original report has tables
**When** converting to Power BI
**Then** Table visuals are created with equivalent columns
**And** Grouping is converted to Group By in the visual
**And** Sorting settings are preserved

### AC3: Chart Visual Conversion
**Given** the original report has charts
**When** converting to Power BI
**Then** Equivalent Power BI chart types are used
**And** Data series mappings are preserved
**And** Axis configurations are converted

### AC4: Matrix Visual Conversion
**Given** the original report has a Matrix
**When** converting to Power BI
**Then** A Matrix visual is created
**And** Row groups become Row fields
**And** Column groups become Column fields
**And** Values are mapped to the Value well

### AC5: Unsupported Visual Handling
**Given** the original report has unsupported visuals (Map, Gauge, custom)
**When** converting to Power BI
**Then** A placeholder visual is created
**And** A text note indicates: "Manual conversion required for [visual type]"
**And** A TODO item is generated

### AC6: Branding Template Application
**Given** a branding template is configured (Story 5.5)
**When** generating the Power BI file
**Then** the template theme is applied
**And** Corporate colors, fonts, and logo are included
**And** Page layout matches template specifications

### AC7: File Output
**Given** Power BI generation completes
**When** the file is ready
**Then** the file is stored with a meaningful name: "{report_name}_converted.pbix"
**And** file integrity is verified (valid ZIP structure)

## Tasks / Subtasks

- [ ] **Task 1: Research PBIX File Structure** (AC: 1, 7)
  - [ ] Document PBIX ZIP structure (DataModel, Report, Metadata)
  - [ ] Identify required JSON schemas for Power BI
  - [ ] Document Layout.json structure for visuals
  - [ ] Document DataModelSchema.json for data model
  - [ ] Evaluate pbi-tools or alternative libraries

- [ ] **Task 2: Create PBIX Builder Service** (AC: 1, 7)
  - [ ] Create `backend/app/services/pbix_builder.py`
  - [ ] Implement PBIX ZIP structure creation
  - [ ] Implement Layout.json generation
  - [ ] Implement DataModelSchema.json generation
  - [ ] Implement file integrity validation
  - [ ] Add ZIP compression handling

- [ ] **Task 3: Create Visual Mapper Service** (AC: 2, 3, 4, 5)
  - [ ] Create RDL to Power BI visual type mapping
  - [ ] Implement Table visual converter
  - [ ] Implement Chart visual converter (Bar, Line, Pie, Area)
  - [ ] Implement Matrix visual converter
  - [ ] Implement placeholder generator for unsupported visuals

- [ ] **Task 4: Implement Table Conversion** (AC: 2)
  - [ ] Map RDL Table to Power BI Table visual
  - [ ] Convert column definitions
  - [ ] Convert grouping to Group By
  - [ ] Preserve sorting settings
  - [ ] Handle column formatting

- [ ] **Task 5: Implement Chart Conversion** (AC: 3)
  - [ ] Map RDL Chart types to Power BI equivalents
  - [ ] Convert CategoryAxis to Category field
  - [ ] Convert ValueAxis to Value field
  - [ ] Convert Series to Legend field
  - [ ] Handle chart-specific options (stacked, clustered)

- [ ] **Task 6: Implement Matrix Conversion** (AC: 4)
  - [ ] Map RDL Matrix to Power BI Matrix
  - [ ] Convert RowGroups to Rows well
  - [ ] Convert ColumnGroups to Columns well
  - [ ] Convert DataCells to Values well
  - [ ] Handle subtotals and totals

- [ ] **Task 7: Implement Unsupported Visual Handler** (AC: 5)
  - [ ] Create placeholder text visual
  - [ ] Generate TODO item for unsupported visuals
  - [ ] Document original visual type in metadata
  - [ ] Include original properties in comments

- [ ] **Task 8: Integrate Branding Template** (AC: 6)
  - [ ] Read branding template from storage
  - [ ] Extract theme (colors, fonts) from template
  - [ ] Apply theme to generated report
  - [ ] Handle case when no template configured

- [ ] **Task 9: Create PBIX Schemas** (AC: 1-7)
  - [ ] Create Pydantic schemas for PBIX metadata
  - [ ] Create schemas for visual configurations
  - [ ] Create schemas for generation result

- [ ] **Task 10: Unit Tests for PBIX Builder** (AC: 1, 2, 3, 4)
  - [ ] Create `backend/tests/test_pbix_builder.py`
  - [ ] Test PBIX ZIP structure validity
  - [ ] Test visual type mapping
  - [ ] Test file integrity validation

## Dev Notes

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| ZIP Handling | zipfile (stdlib) | PBIX is a ZIP file |
| JSON Handling | json (stdlib) | PBIX internal files are JSON |
| Backend | FastAPI | Service layer |
| File Storage | Local filesystem | Store generated files |

### PBIX File Structure

```
report.pbix (ZIP archive)
├── [Content_Types].xml
├── SecurityBindings
├── Metadata
├── DataModel
├── Report/
│   ├── Layout
│   └── StaticResources/
├── Settings
└── DiagramLayout
```

### RDL to Power BI Visual Mapping

| RDL Visual | Power BI Visual | Notes |
|------------|-----------------|-------|
| Table | Table | Direct mapping |
| Matrix | Matrix | Row/Column group conversion |
| Chart (Bar) | Clustered bar chart | |
| Chart (Column) | Clustered column chart | |
| Chart (Line) | Line chart | |
| Chart (Pie) | Pie chart | |
| Chart (Area) | Area chart | |
| Gauge | Card + placeholder | Requires manual |
| Map | Placeholder | Requires manual |
| Subreport | Placeholder | Requires manual |
| Textbox | Text/Card | Simple conversion |
| Rectangle | Container | Layout only |
| Image | Image | If embedded |

### Layout.json Visual Structure

```json
{
  "visualContainers": [
    {
      "x": 100,
      "y": 50,
      "width": 400,
      "height": 300,
      "config": {
        "name": "visual1",
        "layouts": [{
          "position": {
            "x": 0, "y": 0, "width": 400, "height": 300
          }
        }],
        "singleVisual": {
          "visualType": "tableEx",
          "projections": {
            "Values": [
              {"queryRef": "column1"},
              {"queryRef": "column2"}
            ]
          }
        }
      }
    }
  ]
}
```

### Placeholder Visual Template

```json
{
  "visualType": "textbox",
  "objects": {
    "general": [{
      "properties": {
        "paragraphs": [{
          "textRuns": [{
            "value": "TODO: Manual conversion required for [visual_type]"
          }]
        }]
      }
    }]
  }
}
```

### NFR Compliance

- **NFR10**: Must generate valid .pbix files openable in Power BI Desktop
- Validate ZIP structure before returning
- Test with Power BI Desktop during development

### References

- [Source: architecture.md#services/pbix_builder.py] - PBIX builder service
- [Source: architecture.md#services/converter.py] - Converter orchestration
- [Source: epics.md#Story 5.4] - Story requirements
- [Source: prd.md#FR19] - Generate Power BI file requirement
- [Source: prd.md#FR24] - Apply branding template requirement
- [Source: prd.md#FR31] - Auto-apply template requirement
- [Source: prd.md#NFR10] - Valid PBIX requirement

### PRD FRs Covered

- **FR19**: System generates Power BI report file (.pbix) from SSRS report
- **FR24**: System applies branding template to generated Power BI report
- **FR31**: System automatically applies branding template during conversion

### Architecture Compliance Checklist

- [x] PBIX structure follows Power BI specifications
- [x] Visual mapping covers common RDL types
- [x] Unsupported visuals generate TODO items
- [x] Branding template applied when configured
- [x] File integrity validated before storage
- [x] Meaningful file naming convention

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List

1. Created PBIXBuilder service with valid ZIP structure generation
2. Created VisualMapper for RDL to Power BI visual type conversion
3. Implemented Table visual converter with column and field mapping
4. Implemented Chart visual converter (Bar, Column, Line, Area, Pie, Donut)
5. Implemented Matrix visual converter with row/column/value fields
6. Implemented placeholder handler for unsupported visuals (Gauge, Map, Subreport)
7. Created Layout.json generation with visual containers and projections
8. Integrated branding theme support (applies custom colors, fonts when configured)
9. Integrated with converter service for automatic PBIX generation
10. Added 38 unit tests covering all visual types and build scenarios

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-22 | Created PBIX builder service | app/services/pbix_builder.py |
| 2026-01-22 | Integrated with converter service | app/services/converter.py |
| 2026-01-22 | Created unit tests | tests/test_pbix_builder.py |

### File List

**New Files:**
- `app/services/pbix_builder.py` - PBIX Builder with VisualMapper, Layout generation, ZIP creation
- `tests/test_pbix_builder.py` - 38 unit tests for PBIX building

**Modified Files:**
- `app/services/converter.py` - Updated _build_power_bi_report to use PBIXBuilder service
