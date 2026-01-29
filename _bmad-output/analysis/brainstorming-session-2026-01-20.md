---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments: []
session_topic: 'ReportLift - SSRS RDL to Power BI Conversion Tool'
session_goals: 'Define complete product vision, conversion pipeline, and enterprise features'
selected_approach: 'User-guided structured discovery'
techniques_used: ['structured-requirements-gathering', 'pipeline-architecture', 'capability-mapping']
ideas_generated: ['8-step conversion pipeline', 'scoring engine', 'decision gate', 'enterprise features']
context_file: '{project-root}/_bmad/bmm/data/project-context-template.md'
---

# ReportLift - Complete Product Summary

**Facilitator:** RePorter
**Date:** 2026-01-20

---

## Executive Vision

**ReportLift** is an enterprise-grade SSRS-to-Power BI migration platform that analyzes RDL reports, predicts conversion success, automates what's possible, and generates actionable guidance for what requires manual intervention.

**Core Value Proposition:** Transform uncertain, time-consuming report migrations into predictable, measurable, and partially automated workflows.

---

## Core Conversion Pipeline (8 Steps)

### Step 1: RDL Feature Extraction

Parse RDL XML and extract signals across four categories:

| Category | Signals |
|----------|---------|
| **Dataset** | Dataset count, SQL length, stored procs, temp tables, dynamic SQL, parameters |
| **Visual** | Tablix count, charts, subreports, images, maps, custom report items |
| **Expression** | IIF usage, RunningValue, RowNumber, scope-based aggregates, custom VB code |
| **Layout** | Interactive sorting, drillthrough, toggle visibility, page headers/footers |

---

### Step 2: Report Classification

```python
if subreports > 0:
    report_type = "Complex"        # ❌
elif tablix > 0 and charts == 0:
    report_type = "Tabular"        # ✅
elif charts > tablix:
    report_type = "Analytical"     # ⚠️
else:
    report_type = "Mixed"          # ⚠️
```

| Classification | Conversion Outlook |
|---------------|-------------------|
| Tabular | ✅ Best success |
| Paginated | ✅ Good fit for PBI Paginated |
| Analytical | ⚠️ Partial automation |
| Mixed | ⚠️ Partial automation |
| Complex | ❌ High manual effort |

---

### Step 3: Conversion Capability Matrix

| Feature | Auto ✅ | Partial ⚠️ | Manual ❌ |
|---------|:------:|:----------:|:--------:|
| Simple Tablix | ✅ | | |
| Grouped Matrix | ✅ | | |
| Bar/Line Charts | ✅ | | |
| Drillthrough | ✅ | | |
| Conditional Formatting | ✅ | | |
| RunningValue | | ⚠️ | |
| Stored Procedure | | | ❌ |
| Subreports | | | ❌ |
| Custom Code | | | ❌ |

---

### Step 4: Success Scoring Engine

**Algorithm:** Start at 100%, apply penalties, floor at 20%

| Feature | Penalty |
|---------|--------:|
| Subreport | -30% |
| Stored Procedure | -25% |
| Custom Code | -20% |
| Dynamic SQL | -15% |
| RunningValue | -10% |
| Multiple Datasets | -10% |
| Charts (each) | -3% |

**Example:**
```
Tablix: 3, Charts: 2, RunningValue: 1, Stored Proc: 1
Score = 100 - 6 - 10 - 25 = 59%
```

---

### Step 5: Manual Work Detection

| Detected Feature | Manual Action Required |
|-----------------|----------------------|
| Stored Procedure | Rewrite as SELECT query |
| RunningValue | Rebuild using DAX |
| Subreport | Flatten datasets into parent |
| Custom VB Code | Rewrite in DAX/M |
| Toggle Visibility | Redesign as bookmarks/buttons |

Generates explicit TODO checklist for user.

---

### Step 6: Output Contract (JSON)

```json
{
  "reportType": "Tabular",
  "conversionScore": 78,
  "autoConvertible": [
    "3 Tablix visuals",
    "Basic aggregations",
    "Simple parameters"
  ],
  "partiallyConvertible": [
    "RunningValue expressions",
    "Drillthrough actions"
  ],
  "manualRequired": [
    "Rewrite stored procedure as SELECT",
    "Recreate conditional formatting in DAX"
  ],
  "dataSources": {
    "current": "SQL Server",
    "convertibleTo": ["Snowflake"]
  }
}
```

---

### Step 7: Human-Friendly UI Output

```
┌──────────────────────────────────────────────────┐
│  ✅ Report Type: Tabular                         │
│  🔄 Estimated Conversion Success: 78%            │
├──────────────────────────────────────────────────┤
│  ✅ AUTOMATICALLY CONVERTED                      │
│     • All tables and matrix visuals              │
│     • SQL queries (converted to Snowflake)       │
├──────────────────────────────────────────────────┤
│  ⚠️ PARTIALLY CONVERTED                          │
│     • Running totals (requires DAX validation)   │
├──────────────────────────────────────────────────┤
│  ❌ MANUAL WORK REQUIRED                         │
│     • Rewrite stored procedure datasets          │
│     • Redesign drillthrough navigation           │
└──────────────────────────────────────────────────┘
```

---

### Step 8: Go / No-Go Decision Gate

| Score | Decision | Icon | Action |
|-------|----------|------|--------|
| 80-100% | Auto-Convert | 🟢 | Proceed confidently |
| 60-79% | Convert with Warnings | 🟡 | Review flagged items |
| 40-59% | Convert + Checklist | 🟠 | Significant manual work |
| < 40% | Reject | 🔴 | Redesign in Power BI |

---

## Enterprise Features

### SSRS Server Integration
- Connect to SSRS Report Server
- Discover all deployed reports
- Batch analysis with portfolio migration plan
- Preserve folder structure

### Shared Dataset Handling
- Detect shared datasets (`.rsd`)
- Map report dependencies
- Convert to PBI shared datasets
- Preserve relationships

### Post-Conversion Actions
- Deploy to Power BI Service
- Auto-open in Power BI Desktop
- Preview before deployment

### Branding Template Support
- Upload `.pbit` templates
- Apply consistent themes
- Corporate branding across all conversions

### ROI Dashboard
- Man-hours saved calculation
- Cost savings display
- Cumulative value metrics

### Security
- AES-256 credential encryption
- Per-user data isolation
- HTTPS/TLS transmission

### Data Persistence
- SQL database (SQL Server / PostgreSQL)
- User-scoped data storage
- Multi-user / multi-tenant support

### Deployment Flexibility

| Platform | Support |
|----------|---------|
| Windows | ✅ |
| Linux | ✅ |
| Docker | ✅ |
| Kubernetes | ✅ |
| Cloud (Azure/AWS/GCP) | ✅ |

- Deployment target = User choice
- All other config = UI-driven

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        REPORTLIFT                               │
├─────────────────────────────────────────────────────────────────┤
│  UI LAYER (Web)                                                 │
│  ├── Upload RDL / Connect SSRS Server                          │
│  ├── Analysis Dashboard                                         │
│  ├── Conversion Controls                                        │
│  ├── ROI Metrics                                                │
│  └── Settings & Configuration                                   │
├─────────────────────────────────────────────────────────────────┤
│  API LAYER (REST)                                               │
│  ├── POST /analyze      - Single RDL analysis                  │
│  ├── POST /batch        - Server-wide analysis                 │
│  ├── POST /convert      - Execute conversion                   │
│  ├── POST /deploy       - Push to PBI Service                  │
│  └── GET/PUT /settings  - User preferences                     │
├─────────────────────────────────────────────────────────────────┤
│  CORE ENGINE                                                    │
│  ├── RDL XML Parser                                            │
│  ├── Feature Extractor                                         │
│  ├── Report Classifier                                         │
│  ├── Scoring Engine                                            │
│  ├── TODO Generator                                            │
│  ├── Converter Engine                                          │
│  └── PBI Generator                                             │
├─────────────────────────────────────────────────────────────────┤
│  DATA LAYER (SQL Database)                                      │
│  ├── Users (encrypted credentials)                             │
│  ├── Reports (analysis history)                                │
│  ├── Conversions (status, outputs)                             │
│  ├── Templates (branding files)                                │
│  └── Settings (per-user config)                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phased Delivery Roadmap

### Phase 1: MVP (Core Analysis)
- Single RDL upload + analysis
- Feature extraction engine
- Classification + scoring
- JSON + UI output
- Go/No-Go recommendation

### Phase 2: Conversion Engine
- Auto-convert ✅ features
- Generate `.pbix` output
- Open in Power BI Desktop

### Phase 3: Enterprise Features
- SSRS server connection
- Batch analysis
- Shared dataset handling
- User authentication
- SQL persistence

### Phase 4: Production Polish
- Branding template support
- Deploy to PBI Service
- ROI dashboard
- Multi-tenant support
- Container deployment

### Future: Incremental Automation
- RunningValue → DAX automation
- Stored Proc → SELECT rewrite
- Subreport flattening
- Custom VB → DAX translation

---

## Key Differentiators

| Capability | Value |
|-----------|-------|
| **Pre-Conversion Clarity** | Know before you invest time |
| **Actionable TODOs** | Not just scores, but specific tasks |
| **Batch Portfolio Analysis** | Enterprise-wide migration planning |
| **ROI Visibility** | Justify the tool and the migration |
| **Incremental Automation** | Platform gets smarter over time |

---

## Next Steps

This brainstorming output feeds into:
- **Product Brief** - Formal product vision document
- **PRD** - Detailed requirements specification
- **Technical Architecture** - Implementation design
- **Epic & Story Creation** - Development backlog

---

_ReportLift transforms SSRS-to-Power BI migration from a leap of faith into a data-driven, predictable process._
