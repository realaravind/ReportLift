---
stepsCompleted: [1, 2, 3, 4, 5, 6]
status: complete
inputDocuments:
  - '_bmad-output/analysis/brainstorming-session-2026-01-20.md'
date: 2026-01-20
author: RePorter
project_name: reportlift
---

# Product Brief: ReportLift

## Executive Summary

**ReportLift** is an enterprise-grade SSRS-to-Power BI migration intelligence platform that transforms uncertain, budget-busting report conversions into predictable, data-driven workflows. By analyzing RDL files before migration begins, ReportLift provides conversion success scores, automates mechanical transformations, and generates explicit TODO checklists for work requiring human expertise.

In a market with no existing tools and universal reliance on expensive T&M consulting, ReportLift establishes category leadership by delivering what organizations desperately need: **clarity before commitment**.

---

## Core Vision

### Problem Statement

Organizations migrating from SSRS to Power BI face a costly paradox: they know the complexity is significant, but proceed with optimistic estimates anyway. The result is predictable—budget overruns, timeline explosions, and frustrated stakeholders.

### Problem Impact

- **Financial:** T&M consulting costs spiral as "simple" migrations reveal hidden complexity (stored procedures, subreports, custom VB code)
- **Timeline:** Projects routinely exceed estimates by 2-3x, delaying business intelligence modernization
- **Confidence:** IT leaders cannot accurately forecast migration costs, making budget approval a leap of faith
- **Opportunity Cost:** Teams waste skilled developer hours on mechanical conversion work that could be automated

### Why Existing Solutions Fall Short

- **No tools exist** — The market relies entirely on manual analysis and tribal knowledge
- **Microsoft's native path** — Provides basic procedures but doesn't address RDL complexity (stored procedures, expressions, subreports)
- **Consulting estimates** — Based on report counts and gut feel, not systematic feature analysis
- **Manual conversion** — Every migration starts from scratch with no accumulated intelligence

### Proposed Solution

ReportLift delivers **pre-conversion intelligence** through an 8-step analysis pipeline:

1. **Feature Extraction** — Parse RDL XML and extract complexity signals across datasets, visuals, expressions, and layout
2. **Classification** — Categorize reports (Tabular, Analytical, Mixed, Complex) with conversion outlook
3. **Capability Mapping** — Map each feature to Auto/Partial/Manual conversion status
4. **Success Scoring** — Calculate conversion probability using weighted penalty algorithm
5. **TODO Generation** — Produce explicit manual work checklists for non-automatable elements
6. **Structured Output** — Deliver machine-readable JSON for integration and reporting
7. **Human Dashboard** — Present clear visual status with actionable guidance
8. **Decision Gate** — Provide Go/No-Go recommendation based on score thresholds

### Key Differentiators

| Differentiator | Strategic Value |
|----------------|-----------------|
| **First Mover** | No competing tools exist—ReportLift defines the category |
| **Pre-Conversion Clarity** | Know the score before spending a dime, not after commitment |
| **AI-Ready Architecture** | Built for incremental automation as conversion intelligence grows |
| **Thought Leadership** | Positions the company as the authority on SSRS-to-PBI migration |
| **Buyer Alignment** | Serves IT leaders (budget confidence) and consultancies (estimate accuracy) |

---

## Target Users

### Primary Users

**Report Developer ("Dev Dana")**

| Attribute | Details |
|-----------|---------|
| **Role** | BI/Report Developer executing SSRS-to-Power BI migration |
| **Technical Level** | High — fluent in RDL XML, SQL, DAX, Power BI Desktop |
| **Context** | Assigned to one-time migration project with hundreds of reports |
| **Current Pain** | No visibility into report complexity until mid-conversion; estimates are guesswork; hidden features (stored procs, subreports, custom code) cause delays |
| **Goal** | Know upfront what's automatable vs. manual so they can plan work accurately |
| **Success Moment** | "I can see exactly what needs my attention and what the tool handles — no more surprises" |

**User Needs:**

- **Batch Analysis** — Upload hundreds of RDLs and get portfolio-level scoring
- **Individual Deep-Dive** — Drill into any report for detailed feature extraction and TODOs
- **Actionable Output** — Clear distinction between auto-converted elements and manual work items
- **Self-Service** — No workflow overhead; developer picks up reports and works independently

### Secondary Users

Management roles (Team Lead, Manager, QA) operate **outside the system**:

- Team Leads assign work using external project management tools
- Managers track progress through status reports or exports from ReportLift
- QA validates converted Power BI reports independently

ReportLift focuses exclusively on empowering the developer with conversion intelligence.

### User Journey

```
Developer Journey (One-Time Migration)
──────────────────────────────────────
1. UPLOAD    → Batch upload 200+ RDL files from SSRS export
2. ANALYZE   → System scores and classifies all reports
3. TRIAGE    → Developer reviews portfolio: green/yellow/red
4. CONVERT   → Works through reports, guided by TODOs
5. COMPLETE  → Migration finished with predictable effort
```

**Key Insight:** This is a one-time migration tool, not an ongoing operational system. Users engage intensively during the migration project, then the job is done.

---

## Success Metrics

### User Success Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| **Automation Rate** | Percentage of report elements auto-converted without manual intervention | Maximize (>80% for green reports) |
| **Manual Work Items** | Number of TODO items requiring developer attention per report | Minimize |
| **SQL Script Quality** | Generated SQL executes on target database without edits | 100% runnable |
| **Prediction Accuracy** | Conversion score accurately reflects actual effort required | Score within ±10% of reality |

### Business Objectives

| Objective | Success Indicator |
|-----------|-------------------|
| **Product-Market Fit** | Developers report significant time savings vs. manual conversion |
| **Conversion Quality** | Auto-generated artifacts (Power BI, SQL) require minimal post-processing |
| **Enterprise Readiness** | Successfully handles batch analysis of 200+ reports |
| **Thought Leadership** | Recognized as the definitive SSRS-to-Power BI migration solution |

### Key Performance Indicators

| KPI | Measurement |
|-----|-------------|
| **Reports Analyzed** | Total RDL files processed through the platform |
| **Automation Success Rate** | % of reports achieving >70% automation |
| **Zero-Edit SQL Rate** | % of generated SQL scripts that run without modification |
| **Portfolio Coverage** | % of enterprise SSRS reports successfully migrated |

**North Star Metric:** Minimize manual work required to complete a migration — every hour saved is value delivered.

---

## MVP Scope

### Core Features

**Data Input**
- **SSRS Server Connection** — Connect directly to Report Server, browse folder structure, select reports for analysis/conversion
- **RDL File Upload** — Alternative input method for batch upload of exported RDL files

**Analysis Engine**
- **Feature Extraction** — Parse RDL XML, extract complexity signals (datasets, visuals, expressions, layout)
- **Report Classification** — Categorize as Tabular, Analytical, Mixed, or Complex
- **Capability Mapping** — Map each feature to Auto/Partial/Manual conversion status
- **Success Scoring** — Calculate conversion probability with weighted penalty algorithm
- **TODO Generation** — Produce explicit manual work checklists

**Conversion Engine**
- **Power BI Output** — Generate converted Power BI report artifacts
- **Snowflake SQL Generation** — Produce target-platform SQL scripts that run without modification
- **Stored Procedure Handling** — Auto-rewrite SP → SELECT query where possible; flag complex SPs for manual conversion with guidance
- **Branding Template Support** — Upload corporate .pbit template once, apply to all conversions

**User Experience**
- **Portfolio Dashboard** — View all reports with green/yellow/red status at a glance
- **Individual Report Deep-Dive** — Detailed analysis, TODOs, and conversion output per report
- **Single Admin User** — No user management complexity; one authenticated user

### Out of Scope for MVP

| Feature | Rationale | Target Phase |
|---------|-----------|--------------|
| Deploy to Power BI Service | Focus on conversion quality first | Phase 2 |
| ROI Dashboard | Nice-to-have, not core value | Phase 2 |
| Multi-user Management | Single admin sufficient for initial use | Phase 2 |
| Shared Dataset Handling | Complex dependency mapping deferred | Phase 2 |
| Advanced SP Automation | Start with simple SP rewrite, expand later | Future |

### MVP Success Criteria

| Criteria | Validation |
|----------|------------|
| **Connects to SSRS** | Successfully authenticates and browses Report Server |
| **Analyzes 200+ Reports** | Batch analysis completes with accurate scoring |
| **Generates Runnable SQL** | Snowflake scripts execute without manual edits |
| **Converts Simple Reports** | Green-scored reports produce working Power BI output |
| **Handles Stored Procedures** | Auto-rewrites simple SPs, clearly flags complex ones |
| **Applies Branding** | Template applied consistently across all conversions |

### Future Vision

**Phase 2: Production Polish**
- Deploy directly to Power BI Service/Workspace
- ROI dashboard showing hours/cost saved
- Multi-user support with role-based access

**Phase 3: Intelligence Expansion**
- Advanced stored procedure analysis with AI-assisted rewrite
- Subreport flattening automation
- Custom VB code → DAX translation
- RunningValue → DAX automation

**Phase 4: Platform Growth**
- Additional target platforms beyond Snowflake (Databricks, BigQuery)
- SSRS-to-Paginated Reports conversion path
- White-label/embedded offering for consulting partners

