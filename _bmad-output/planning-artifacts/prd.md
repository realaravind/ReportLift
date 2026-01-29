---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish']
inputDocuments:
  - '_bmad-output/planning-artifacts/product-brief-reportlift-2026-01-20.md'
  - '_bmad-output/analysis/brainstorming-session-2026-01-20.md'
workflowType: 'prd'
documentCounts:
  brief: 1
  research: 0
  brainstorming: 1
  projectDocs: 0
date: 2026-01-20
classification:
  projectType: 'Web App (Self-Hosted)'
  domain: 'Business Intelligence / Data Migration'
  complexity: 'Medium'
  projectContext: 'Greenfield'
  deploymentModel: 'On-Premises / Container'
---

# Product Requirements Document - ReportLift

**Author:** RePorter
**Date:** 2026-01-20

## Executive Summary

ReportLift is an enterprise-grade SSRS-to-Power BI migration intelligence platform that transforms uncertain, budget-busting report conversions into predictable, data-driven workflows. By analyzing RDL files before migration begins, ReportLift provides conversion success scores, automates mechanical transformations, and generates explicit TODO checklists for work requiring human expertise.

**Key Value Proposition:** Know the conversion complexity before spending a dime — not after commitment.

**Target User:** Report Developers executing SSRS-to-Power BI migrations within enterprise environments.

**Deployment Model:** Self-hosted on-premises (Windows/Linux/Container) with local AI (Ollama) for privacy-preserving intelligent conversion.

## Success Criteria

### User Success

**Primary Success Moment:** The first auto-converted report opens cleanly in Power BI Desktop — this is when user trust is established.

| Metric | Definition | Target |
|--------|------------|--------|
| **Automation Rate** | % of report elements auto-converted without manual intervention | >80% for green-scored reports |
| **Manual Work Reduction** | TODO items requiring developer attention | Minimize per report |
| **Conversion Accuracy** | Auto-generated Power BI reports function correctly | 100% accuracy for supported features |
| **SQL Script Quality** | Generated Snowflake SQL executes without modification | 100% runnable |
| **Prediction Accuracy** | Conversion score reflects actual conversion effort | Within ±10% of reality |

### Business Success

| Objective | Success Indicator |
|-----------|-------------------|
| **Product-Market Fit** | Developers report significant time savings vs. manual conversion |
| **Conversion Quality** | Auto-generated artifacts require minimal post-processing |
| **Enterprise Readiness** | Successfully handles batch analysis of 200+ reports |
| **Thought Leadership** | Recognized as the definitive SSRS-to-Power BI migration solution |

### Technical Success

| Metric | Definition | Target |
|--------|------------|--------|
| **Conversion Accuracy** | Auto-generated reports match expected output | Primary metric — correctness over speed |
| **SP Rewrite Success** | Simple stored procedures correctly converted to SELECT | High accuracy for common patterns |
| **Feature Coverage** | % of RDL features correctly parsed and handled | Comprehensive extraction |
| **Stability** | System handles enterprise-scale batch operations | 200+ reports without failure |

### Measurable Outcomes

**North Star Metric:** Minimize manual work required to complete a migration — every hour saved is value delivered.

| KPI | Measurement |
|-----|-------------|
| **Reports Analyzed** | Total RDL files processed through the platform |
| **Automation Success Rate** | % of reports achieving >70% automation |
| **Zero-Edit SQL Rate** | % of generated SQL scripts that run without modification |
| **Clean Open Rate** | % of converted reports that open cleanly in Power BI |

## Product Scope

### MVP - Minimum Viable Product

The MVP proves conversion accuracy with a single-report workflow before scaling to batch operations.

**Data Input**
- SSRS Server Connection — browse and select reports directly

**Analysis Engine**
- Feature Extraction, Report Classification, Capability Mapping
- Success Scoring with weighted penalty algorithm
- TODO Generation for manual work items

**Conversion Engine**
- Power BI Output — generate working .pbix artifacts
- Snowflake SQL Generation — runnable scripts without edits
- Stored Procedure Handling — rule-based rewrite with AI assist for complex patterns
- Branding Template Support — upload once, apply to all

**User Experience**
- Individual Report Analysis and Conversion
- Single Admin User

### Growth Features (Post-MVP)

- Auto-analysis on SSRS connection
- Portfolio dashboard (green/yellow/red summary with multi-select)
- Batch analysis and conversion
- RDL file upload alternative
- Deploy directly to Power BI Service/Workspace
- ROI Dashboard showing hours/cost saved
- Multi-user support with role-based access
- Shared Dataset handling

### Vision (Future)

- Advanced SP analysis with full AI-powered rewrite
- Subreport flattening automation
- Custom VB code → DAX translation
- Additional target platforms (Databricks, BigQuery)
- White-label/embedded offering for consulting partners

## User Journeys

### Journey 1: Sys Admin — Server Provisioning

**Persona:** Sam, Infrastructure Administrator
**Context:** IT has approved ReportLift for the SSRS migration project. Sam needs to provision the environment.

**Opening Scene:**
Sam receives a request to provision infrastructure for ReportLift. The team needs it running within corporate network — no cloud dependencies. Sam checks the requirements: Windows Server, Linux, or container deployment options.

**Rising Action:**
1. Sam provisions a Windows Server VM (or Linux/Docker based on preference)
2. Ensures network access to SSRS Report Server
3. Ensures network access to target database (Snowflake)
4. Opens required ports for web UI access
5. Hands off to Tech Lead for application installation

**Resolution:**
Infrastructure ready. Sam's job is done — clean handoff to Tech Lead.

**Requirements Revealed:**
- Clear infrastructure requirements documentation
- Flexible deployment options (Windows/Linux/Container)
- Network connectivity requirements clearly specified
- No cloud dependencies — fully on-prem capable

---

### Journey 2: Tech Lead — Installation & Configuration

**Persona:** Taylor, Technical Lead
**Context:** Server is provisioned. Taylor needs to install ReportLift and configure it for the team.

**Opening Scene:**
Taylor receives credentials for the provisioned server. The migration project kicks off next week — ReportLift needs to be ready.

**Rising Action:**
1. Taylor downloads and installs ReportLift application
2. Configures connection to SSRS Report Server (credentials, URL)
3. Configures target database connection (Snowflake credentials)
4. Uploads corporate Power BI branding template (.pbit)
5. Verifies connectivity — SSRS reports visible, Snowflake connection successful
6. Creates admin credentials for the team
7. Sends Dana the URL and login

**Climax:**
Taylor browses the SSRS Report Server through ReportLift — all 200+ reports visible. Connection verified. Ready to go.

**Resolution:**
ReportLift configured and ready. Taylor briefs Dana: "You're all set — log in and start analyzing."

**Requirements Revealed:**
- Simple installation process (installer or container image)
- SSRS connection configuration (URL, credentials, authentication)
- Snowflake connection configuration (credentials, warehouse, schema)
- Branding template upload (one-time .pbit upload)
- Connection verification/test functionality
- Admin user setup

---

### Journey 3: Report Developer — First Conversion (MVP Success Path)

**Persona:** Dana, Report Developer
**Context:** Migration project assigned — 200 SSRS reports need to move to Power BI with Snowflake backend. Dana has never used ReportLift before.

**Opening Scene:**
Dana logs into ReportLift for the first time. The interface shows a connection to SSRS Report Server. Dana can browse the familiar folder structure. Dana thinks: "Let's see if this thing actually works."

**Rising Action:**
1. Dana browses to a folder and selects a single report to test — a mid-complexity tabular report with 2 datasets
2. Clicks "Analyze" — within seconds, sees the score: **78% — Convert with Warnings**
3. Reviews the analysis: 2 tables auto-convertible, 1 stored procedure flagged for rewrite
4. Sees the TODO list: "Rewrite SP_GetSalesData as SELECT query"
5. Decides to proceed — clicks "Convert"
6. ReportLift generates: Power BI report (.pbix) + Snowflake SQL scripts
7. Dana opens the .pbix in Power BI Desktop — **it opens cleanly**

**Climax:**
Dana runs the report against Snowflake. Compares the output to the original SSRS report. **The data matches.** The visuals look right. The branding template is applied.

Dana thinks: "Holy... this actually works."

**Resolution:**
Trust established. Dana now understands: green reports convert automatically, yellow need attention, red need redesign. The 200-report mountain suddenly looks climbable.

**Requirements Revealed:**
- SSRS folder browsing (familiar structure)
- Single report selection and analysis
- Clear score interpretation (green/yellow/red)
- Detailed analysis breakdown (what's auto vs. manual)
- TODO list generation
- One-click conversion
- Power BI artifact generation (.pbix)
- Snowflake SQL generation
- Branding template application

---

### Journey 4: Report Developer — Batch Migration (Post-MVP)

> **Note:** This journey describes Phase 2 functionality after batch operations are implemented.

**Persona:** Dana, Report Developer
**Context:** First report worked. Now Dana needs to tackle the full portfolio.

**Opening Scene:**
Dana returns to ReportLift, confidence building. 200 reports to go. Time to scale up.

**Rising Action:**
1. Dana selects the root SSRS folder — all 200 reports
2. Clicks "Batch Analyze" — portfolio analysis begins
3. Dashboard populates: **140 green, 45 yellow, 15 red**
4. Dana sorts by score — starts with the green reports
5. Batch converts 50 green reports — all generate successfully
6. Works through yellow reports methodically, addressing TODOs
7. Escalates red reports to Tech Lead for redesign decisions

**Climax:**
Day 3: 180 reports converted and verified. The remaining 20 are known complex cases with clear action plans.

**Resolution:**
Migration on track. Dana reports to management: "We'll finish ahead of schedule. ReportLift eliminated 80% of the manual analysis work."

**Requirements Revealed (Phase 2):**
- Folder/batch selection
- Batch analysis with progress indication
- Portfolio dashboard (green/yellow/red summary)
- Sorting and filtering by score
- Batch conversion capability
- Progress tracking
- Export capability for reporting to management

---

### Journey 5: Report Developer — Error Recovery (Edge Case)

**Persona:** Dana, Report Developer
**Context:** A converted report doesn't work as expected.

**Opening Scene:**
Dana converts a yellow-scored report. Opens it in Power BI — error on load. Something went wrong.

**Rising Action:**
1. Dana returns to ReportLift, opens the report analysis
2. Reviews the detailed breakdown — sees a flagged expression that was partially converted
3. Checks the TODO list — finds guidance: "RunningValue expression requires manual DAX recreation"
4. Opens the generated .pbix in Power BI Desktop
5. Locates the problematic measure, applies the manual fix per guidance
6. Saves and tests — report now works

**Resolution:**
Dana learns: yellow reports need attention. The tool told her exactly where to look and what to fix. The error wasn't a surprise — it was documented.

**Requirements Revealed:**
- Detailed analysis breakdown (specific expressions/features flagged)
- Clear guidance for manual interventions
- TODO items linked to specific report elements
- Generated artifacts are editable (not black boxes)
- Error messages are actionable

---

### Journey Requirements Summary

| Capability Area | Revealed By Journey | MVP/Post-MVP |
|-----------------|---------------------|--------------|
| **Infrastructure** | Sys Admin — deployment flexibility, network requirements | MVP |
| **Installation & Config** | Tech Lead — SSRS connection, Snowflake config, branding upload | MVP |
| **Single Report Analysis** | Dana Success — instant scoring, clear breakdown | MVP |
| **Conversion Engine** | Dana Success — .pbix generation, SQL generation | MVP |
| **Portfolio Management** | Dana Batch — dashboard, sorting, filtering, batch ops | Post-MVP |
| **Error Handling** | Dana Error — detailed guidance, actionable TODOs | MVP |

## Domain-Specific Requirements

### Authentication & Identity

| System | Authentication Method | Details |
|--------|----------------------|---------|
| **ReportLift Login** | Windows/AD Pass-through | Users authenticate with corporate AD credentials |
| **SSRS Connection** | AD Pass-through | User's AD identity used to access Report Server |
| **Snowflake Connection** | SSO/OAuth | Federated authentication via corporate IdP |

**Pass-through Authentication Flow:**
1. User logs into ReportLift with AD credentials
2. ReportLift uses those credentials to authenticate to SSRS
3. User only sees reports they have permission to access in SSRS
4. Snowflake access via OAuth token from corporate IdP

### Credential & Secret Management

| Requirement | Implementation |
|-------------|----------------|
| **Storage** | Encrypted local configuration file |
| **Encryption** | AES-256 or equivalent for secrets at rest |
| **Scope** | Connection strings, OAuth client secrets, API keys |
| **Access** | Only ReportLift service account can decrypt |

### Audit & Compliance

| Audit Event | Data Captured |
|-------------|---------------|
| **User Login** | Username, timestamp, success/failure |
| **Report Analysis** | Username, report name, timestamp, score |
| **Report Conversion** | Username, report name, timestamp, output files |
| **Configuration Change** | Username, setting changed, old/new value |

**Audit Log Requirements:**
- Immutable log entries (append-only)
- Retention until explicitly deleted by admin
- Exportable for compliance reporting

### Enterprise Integration

| Integration Point | Requirement |
|-------------------|-------------|
| **Active Directory** | Windows Authentication for user login |
| **Corporate IdP** | OAuth/OIDC for Snowflake SSO (Azure AD, Okta, etc.) |
| **SSRS Report Server** | Windows Integrated Authentication |
| **Snowflake** | OAuth token-based access |

## Innovation & Novel Patterns

### Market Position

ReportLift is the first dedicated tool for SSRS-to-Power BI migration. The market currently relies entirely on manual analysis and tribal knowledge. ReportLift defines this category.

### Local AI-Powered Conversion Engine

The core innovation is using locally-hosted LLM inference (Ollama) for intelligent conversion:

| Capability | AI Application |
|------------|----------------|
| **SP → SELECT Rewrite** | LLM analyzes stored procedure logic and generates equivalent SELECT statement |
| **Expression Translation** | LLM converts SSRS expression syntax to DAX measures or M queries |
| **Complexity Classification** | AI-assisted pattern recognition for report scoring |
| **TODO Generation** | LLM generates human-readable guidance for manual work items |

### On-Premises AI Advantage

Unlike cloud-based AI tools, ReportLift's Ollama integration keeps all data within the corporate network:
- No report definitions sent to external services
- No SQL or business logic exposed to cloud providers
- Compliant with enterprise data residency requirements
- Works in air-gapped environments

### Competitive Landscape

| Approach | Gap ReportLift Fills |
|----------|----------------------|
| **Manual Conversion** | Time-consuming, error-prone, no predictability |
| **Microsoft Native** | Doesn't handle complexity (SPs, expressions, subreports) |
| **Generic AI Tools** | Data privacy concerns, not SSRS-specific |

### Validation Approach

| Validation Method | Purpose |
|-------------------|---------|
| **Corpus Testing** | Run against library of real SSRS reports with known complexity |
| **Output Comparison** | Compare generated Power BI output to manually-converted baseline |
| **SP Rewrite Verification** | Execute generated SELECT against same data as original SP |
| **User Feedback Loop** | Track prediction accuracy vs. actual conversion effort |

### Risk Mitigation

| Risk | Mitigation |
|------|------------|
| **LLM Hallucination** | Validate generated SQL syntax before output; flag uncertain conversions |
| **Model Quality** | Start with conservative scoring; improve based on validation data |
| **Ollama Dependency** | Abstract AI interface to allow model swapping; fallback to rule-based conversion |
| **Enterprise Adoption** | Local deployment eliminates cloud security objections |

## Web App Specific Requirements

### Technical Architecture

| Aspect | Decision |
|--------|----------|
| **Application Type** | Single Page Application (SPA) with multi-page navigation |
| **Deployment** | On-premises (Windows/Linux/Container) |
| **Browser Support** | Chrome, Internet Explorer, Microsoft Edge |
| **Offline Support** | Not required — always-connected enterprise environment |

### Frontend Architecture

**SPA with Professional Multi-Page Feel:**
- Modern SPA framework for responsive, fluid interactions
- Multi-page navigation structure for logical separation:
  - Connection/Setup page
  - Report Browser page
  - Report Analysis/Detail page
  - Conversion Output page
  - Settings/Configuration page
- No full page reloads during workflow — smooth transitions

### Browser Compatibility

| Browser | Version | Support Level |
|---------|---------|---------------|
| **Google Chrome** | Latest stable | Full support |
| **Microsoft Edge** | Latest stable | Full support |
| **Internet Explorer** | 11 | Basic support (legacy enterprise) |

**IE11 Considerations:**
- May require polyfills for modern JavaScript features
- Test critical workflows on IE11
- Graceful degradation acceptable for non-critical features

### Performance Targets

| Operation | Target |
|-----------|--------|
| **Initial Load** | Dashboard renders within 3 seconds |
| **SSRS Connection** | Report list retrieved within 5 seconds |
| **Per-Report Analysis** | Score calculated within 2 seconds per report |

### Security (Web-Specific)

- Windows Authentication / AD integration for login
- Session management with secure tokens
- HTTPS required for all traffic
- CORS configured for API security
- No sensitive data stored in browser local storage

## Project Scoping & Phased Development

### MVP Strategy

**Approach:** Problem-Solving MVP — Deliver core conversion value for a single report workflow before scaling to batch operations.

**Philosophy:** Prove the conversion engine works accurately before adding portfolio management complexity. A developer who can convert ONE report successfully will trust the tool for hundreds.

### MVP Feature Set (Phase 1)

**Core User Journey Supported:**
- Dana's First Conversion (single report success path)
- Taylor's Installation & Configuration

**Must-Have Capabilities:**

| Capability | Description |
|------------|-------------|
| **SSRS Connection** | Connect to Report Server, browse folder structure |
| **Single Report Selection** | Select one report for analysis |
| **On-Demand Analysis** | Click "Analyze" to score and extract features |
| **Conversion Score** | Green/yellow/red with percentage |
| **TODO Generation** | List of manual work items |
| **Single Report Conversion** | Generate .pbix + Snowflake SQL |
| **SP Rewrite (Rule-based + AI)** | Pattern-match common SPs, AI assist for complex |
| **Branding Template** | Apply uploaded .pbit template |
| **AD Authentication** | Windows pass-through for SSRS |
| **Snowflake OAuth** | SSO for target database |

**Explicitly NOT in MVP:**
- Batch analysis / batch conversion
- Auto-analysis on SSRS connect
- Portfolio dashboard with multi-select
- RDL file upload
- Multi-user support
- ROI dashboard

### Post-MVP Features

**Phase 2: Batch & Portfolio**
- Auto-analysis on SSRS connection
- Portfolio dashboard (green/yellow/red summary)
- Multi-select reports for batch conversion
- Batch conversion queue
- Progress tracking
- RDL file upload alternative
- Expanded AI patterns for SP rewrite

**Phase 3: Enterprise & Scale**
- Multi-user support with roles
- Deploy to Power BI Service
- ROI dashboard
- Shared dataset handling
- Full AI-powered SP rewrite
- Additional target platforms (Databricks, BigQuery)

### Risk Mitigation

| Risk Category | Risk | Mitigation |
|---------------|------|------------|
| **Technical** | SP Rewrite Accuracy | Start with rule-based patterns; AI assists on edge cases; flag uncertain for manual |
| **Technical** | Power BI Generation | Focus on common report types first; expand visual support iteratively |
| **Technical** | Ollama Performance | Test with representative report complexity; optimize prompts |
| **Market** | Adoption Hesitancy | Single-report MVP proves value before batch commitment |
| **Market** | Accuracy Trust | Visible scoring and TODO transparency builds confidence |
| **Resource** | Scope Creep | Phase 2 features explicitly deferred; MVP boundary is clear |

## Functional Requirements

### Connection & Data Source Management

- FR1: Admin can configure connection to an SSRS Report Server (URL, authentication method)
- FR2: Admin can configure connection to a Snowflake database (credentials, warehouse, schema)
- FR3: Admin can test SSRS connection and verify successful authentication
- FR4: Admin can test Snowflake connection and verify successful authentication
- FR5: User can browse SSRS Report Server folder structure
- FR6: User can view list of reports available in a selected SSRS folder
- FR7: System respects SSRS permissions — user only sees reports they have access to

### Report Analysis

- FR8: User can select a single report for analysis
- FR9: User can trigger on-demand analysis of a selected report
- FR10: System extracts features from RDL file (datasets, visuals, expressions, layout)
- FR11: System classifies report type (Tabular, Analytical, Mixed, Complex)
- FR12: System calculates conversion success score (percentage)
- FR13: System assigns conversion status (green/yellow/red) based on score thresholds
- FR14: System identifies stored procedures used in report datasets
- FR15: System identifies expressions requiring conversion attention
- FR16: System generates TODO list of manual work items for the report
- FR17: User can view detailed analysis breakdown for a report

### Report Conversion

- FR18: User can initiate conversion of an analyzed report
- FR19: System generates Power BI report file (.pbix) from SSRS report
- FR20: System generates Snowflake SQL scripts for report data sources
- FR21: System rewrites simple stored procedures as SELECT statements (rule-based)
- FR22: System uses AI (Ollama) to assist with complex SP rewrite scenarios
- FR23: System flags uncertain SP conversions for manual review
- FR24: System applies branding template to generated Power BI report
- FR25: User can download generated Power BI file (.pbix)
- FR26: User can download generated Snowflake SQL scripts
- FR27: User can view conversion output summary (what was converted, what needs attention)

### Branding & Templates

- FR28: Admin can upload a Power BI branding template (.pbit file)
- FR29: Admin can view currently configured branding template
- FR30: Admin can replace existing branding template with a new one
- FR31: System automatically applies branding template during conversion

### Authentication & Security

- FR32: User can authenticate using Windows/Active Directory credentials
- FR33: System passes user's AD identity through to SSRS for report access
- FR34: System authenticates to Snowflake using OAuth/SSO via corporate IdP
- FR35: System stores credentials in encrypted configuration file
- FR36: System requires HTTPS for all web traffic
- FR37: System manages user sessions with secure tokens

### Configuration & Administration

- FR38: Admin can access application settings/configuration page
- FR39: Admin can configure SSRS connection parameters
- FR40: Admin can configure Snowflake connection parameters
- FR41: Admin can configure OAuth/IdP settings for Snowflake SSO
- FR42: Admin can view system status and connection health

### Audit & Logging

- FR43: System logs user login events (username, timestamp, success/failure)
- FR44: System logs report analysis events (user, report, timestamp, score)
- FR45: System logs report conversion events (user, report, timestamp, output files)
- FR46: System logs configuration changes (user, setting, old value, new value)
- FR47: Admin can view audit logs
- FR48: Admin can export audit logs for compliance reporting

### AI Integration (Ollama)

- FR49: System connects to local Ollama instance for AI-assisted conversion
- FR50: System sends stored procedure logic to Ollama for analysis
- FR51: System receives and applies AI-generated SELECT statement rewrites
- FR52: System uses AI to generate human-readable TODO guidance
- FR53: Admin can configure Ollama connection settings

## Non-Functional Requirements

### Security

| Requirement | Specification |
|-------------|---------------|
| **Authentication** | Windows/AD pass-through authentication required |
| **Credential Storage** | All credentials encrypted at rest (AES-256 or equivalent) |
| **Transport Security** | HTTPS required for all web traffic |
| **Session Management** | Secure tokens with configurable timeout |
| **SSRS Permissions** | User access respects underlying SSRS permission model |
| **Snowflake Auth** | OAuth/SSO via corporate IdP (no stored passwords) |

### Integration

| Integration | Requirement |
|-------------|-------------|
| **SSRS Report Server** | Must connect via Windows Integrated Authentication |
| **Snowflake** | Must support OAuth/OIDC authentication flow |
| **Ollama** | Must connect to locally-hosted Ollama instance |
| **Power BI** | Must generate valid .pbix files openable in Power BI Desktop |

**Integration Failure Handling:**
- Clear error messages when connections fail
- Connection test functionality for each integration
- Graceful degradation if Ollama unavailable (fall back to rule-based only)

### Reliability

| Requirement | Specification |
|-------------|---------------|
| **Availability** | No 24/7 requirement; acceptable downtime for maintenance |
| **Error Recovery** | System recovers gracefully from transient errors |
| **Data Integrity** | Conversion outputs are complete or not generated (no partial files) |
| **Stability** | System handles typical workload without crashes |

### Data Retention

| Data Type | Retention Policy |
|-----------|------------------|
| **Audit Logs** | Retained until explicitly deleted by admin |
| **Analysis History** | Retained until explicitly deleted by admin |
| **Conversion Outputs** | Available for download; storage managed by admin |
| **Configuration** | Persisted across restarts |

### Deployment

| Requirement | Specification |
|-------------|---------------|
| **Platforms** | Windows Server, Linux, Docker container |
| **Dependencies** | Self-contained; minimal external dependencies |
| **Installation** | Simple installer or container image |
| **Updates** | Manual update process (no auto-update requirement) |

### Browser Support

| Browser | Support Level |
|---------|---------------|
| **Chrome** | Full support (latest stable) |
| **Edge** | Full support (latest stable) |
| **Internet Explorer 11** | Basic support (graceful degradation) |
