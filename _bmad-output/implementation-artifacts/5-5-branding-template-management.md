# Story 5.5: Branding Template Management

Status: done

## Story

As an **admin**,
I want **to upload and manage a Power BI branding template**,
so that **all converted reports have consistent corporate branding**.

## Acceptance Criteria

### AC1: View Template Status
**Given** the admin is on the Settings page
**When** viewing the Branding section
**Then** the current template status is displayed:
  - If configured: Template name, upload date, preview thumbnail
  - If not configured: "No branding template configured"

### AC2: Upload Template
**Given** no template is configured
**When** the admin clicks "Upload Template"
**Then** a file picker allows selection of .pbit files
**And** only .pbit files are accepted
**And** file size is validated (max 50MB)

### AC3: Template Validation
**Given** a valid .pbit file is selected
**When** upload completes
**Then** the template is validated (opens without errors)
**And** success message: "Branding template uploaded successfully"
**And** the template preview updates

### AC4: Replace Template
**Given** a template already exists
**When** the admin uploads a new template
**Then** they are prompted: "Replace existing template?"
**And** selecting "Yes" replaces the old template
**And** selecting "No" cancels the upload

### AC5: Remove Template
**Given** a template is configured
**When** the admin clicks "Remove Template"
**Then** they are prompted to confirm
**And** removing clears the template
**And** future conversions will not have branding applied

### AC6: Download Current Template
**Given** a template is configured
**When** the admin clicks "Download Current"
**Then** the current template file is downloaded
**And** useful for backup or sharing across environments

## Tasks / Subtasks

- [ ] **Task 1: Create Template Database Model** (AC: 1, 3, 5)
  - [ ] Create `backend/app/models/branding_template.py`
  - [ ] Add fields: id, name, file_path, uploaded_at, uploaded_by, file_size, is_active
  - [ ] Create Alembic migration
  - [ ] Add unique constraint (only one active template)

- [ ] **Task 2: Create Template Storage Service** (AC: 2, 3, 5, 6)
  - [ ] Create `backend/app/services/template_service.py`
  - [ ] Implement file upload to storage directory
  - [ ] Implement file validation (ZIP structure, PBIT format)
  - [ ] Implement file retrieval for download
  - [ ] Implement file deletion on remove
  - [ ] Handle storage path configuration

- [ ] **Task 3: Create Template Validator** (AC: 2, 3)
  - [ ] Validate file extension (.pbit only)
  - [ ] Validate file size (max 50MB)
  - [ ] Validate PBIT structure (valid ZIP with required components)
  - [ ] Extract theme metadata for preview

- [ ] **Task 4: Create Template API Endpoints** (AC: 1-6)
  - [ ] Create `backend/app/api/routes/templates.py`
  - [ ] Add `GET /api/v1/templates/current` - Get current template info
  - [ ] Add `POST /api/v1/templates` - Upload new template
  - [ ] Add `DELETE /api/v1/templates/{template_id}` - Remove template
  - [ ] Add `GET /api/v1/templates/{template_id}/download` - Download template
  - [ ] Register routes in main.py

- [ ] **Task 5: Create Template Pydantic Schemas** (AC: 1-6)
  - [ ] Create `backend/app/schemas/template.py`
  - [ ] Create TemplateResponse schema
  - [ ] Create TemplateUploadResponse schema
  - [ ] Create TemplateStatusResponse schema

- [ ] **Task 6: Create Frontend Template Hook** (AC: 1-6)
  - [ ] Create `frontend/src/hooks/useTemplate.ts`
  - [ ] Implement query for current template status
  - [ ] Implement mutation for upload
  - [ ] Implement mutation for delete
  - [ ] Handle download action

- [ ] **Task 7: Create Template Management UI** (AC: 1-6)
  - [ ] Create `frontend/src/components/settings/TemplateUpload.tsx`
  - [ ] Create template status display component
  - [ ] Create file upload component with drag-and-drop
  - [ ] Create replace confirmation dialog
  - [ ] Create remove confirmation dialog
  - [ ] Add download button
  - [ ] Add file size and type validation feedback

- [ ] **Task 8: Integrate with Settings Page** (AC: 1)
  - [ ] Add Branding tab to Settings page
  - [ ] Display template management component
  - [ ] Handle loading and error states

- [ ] **Task 9: Audit Logging for Template Changes** (AC: 3, 4, 5)
  - [ ] Log template upload events
  - [ ] Log template replacement events
  - [ ] Log template removal events

## Dev Notes

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| File Upload | python-multipart | Handle multipart form data |
| ZIP Handling | zipfile | Validate PBIT structure |
| Storage | Local filesystem | Store template files |
| Frontend Upload | shadcn/ui + react-dropzone | File upload UI |

### API Endpoints

**GET /api/v1/templates/current**
```json
Response (configured): {
  "data": {
    "id": "uuid",
    "name": "Corporate_Theme.pbit",
    "uploaded_at": "2026-01-21T10:30:00Z",
    "uploaded_by": "admin@company.com",
    "file_size": 1048576,
    "is_active": true
  }
}

Response (not configured): {
  "data": null,
  "meta": {
    "message": "No branding template configured"
  }
}
```

**POST /api/v1/templates**
```
Request: multipart/form-data
  - file: .pbit file

Response: {
  "data": {
    "id": "uuid",
    "name": "Corporate_Theme.pbit",
    "uploaded_at": "2026-01-21T10:30:00Z",
    "file_size": 1048576
  },
  "meta": {
    "message": "Branding template uploaded successfully"
  }
}
```

**DELETE /api/v1/templates/{template_id}**
```json
Response: {
  "data": {
    "id": "uuid",
    "deleted": true
  },
  "meta": {
    "message": "Branding template removed"
  }
}
```

### PBIT File Structure

PBIT (Power BI Template) is a ZIP file containing:
```
template.pbit
├── [Content_Types].xml
├── DataModelSchema
├── DiagramLayout
├── Report/
│   ├── Layout
│   └── StaticResources/
│       ├── RegisteredResources/
│       │   └── (logo images, etc.)
├── Settings
└── Metadata
```

### Validation Rules

| Rule | Validation | Error Message |
|------|------------|---------------|
| Extension | Must be .pbit | "Only .pbit files are accepted" |
| Size | Max 50MB | "File size exceeds 50MB limit" |
| Structure | Valid ZIP | "Invalid file: not a valid template" |
| Content | Has Layout file | "Invalid template: missing required components" |

### File Storage Structure

```
storage/
├── templates/
│   ├── current/
│   │   └── {template_id}.pbit
│   └── archive/
│       └── {old_template_id}.pbit
```

### Theme Extraction (for Preview)

Extract from template for display:
- Primary color
- Secondary color
- Font family
- Logo (if embedded)

### References

- [Source: architecture.md#services/template_service.py] - Template service location
- [Source: architecture.md#API Endpoints] - API patterns
- [Source: epics.md#Story 5.5] - Story requirements
- [Source: prd.md#FR28] - Upload branding template
- [Source: prd.md#FR29] - View current template
- [Source: prd.md#FR30] - Replace template

### PRD FRs Covered

- **FR28**: Admin can upload a Power BI branding template (.pbit file)
- **FR29**: Admin can view currently configured branding template
- **FR30**: Admin can replace existing branding template with a new one

### Architecture Compliance Checklist

- [x] Template stored in configured storage directory
- [x] Database record tracks template metadata
- [x] Only one active template at a time
- [x] File validation before storage
- [ ] Audit logging for all template operations (deferred to Epic 7)
- [x] API follows REST conventions

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List

1. Created BrandingTemplate database model with active flag, metadata, and relationships
2. Created template storage service with file upload, validation, and retrieval
3. Created template validator for .pbit files (checks ZIP structure, Layout component)
4. Created Pydantic schemas for template operations
5. Created API endpoints (GET /current, POST /, DELETE /{id}, GET /{id}/download)
6. Created useTemplate React hook with mutations for upload, delete, download
7. Created TemplateUpload component with drag-and-drop, replace/delete dialogs
8. Integrated Branding tab into Settings page
9. Added 21 unit tests for template service
10. Theme metadata extraction from PBIT files for preview

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-22 | Created branding template model | app/models/branding_template.py |
| 2026-01-22 | Created template service | app/services/template_service.py |
| 2026-01-22 | Created template schemas | app/schemas/template.py |
| 2026-01-22 | Created template API routes | app/api/routes/templates.py |
| 2026-01-22 | Created frontend hook | frontend/src/hooks/useTemplate.ts |
| 2026-01-22 | Created TemplateUpload component | frontend/src/components/settings/TemplateUpload.tsx |
| 2026-01-22 | Updated Settings page | frontend/src/pages/Settings.tsx |
| 2026-01-22 | Created unit tests | tests/test_template_service.py |

### File List

**New Files:**
- `app/models/branding_template.py` - BrandingTemplate database model
- `app/services/template_service.py` - Template storage, validation, and retrieval service
- `app/schemas/template.py` - Pydantic schemas for template operations
- `app/api/routes/templates.py` - REST API endpoints for template management
- `frontend/src/hooks/useTemplate.ts` - React Query hooks for template operations
- `frontend/src/components/settings/TemplateUpload.tsx` - Template management UI component
- `tests/test_template_service.py` - 21 unit tests for template service

**Modified Files:**
- `app/models/__init__.py` - Added BrandingTemplate export
- `app/api/routes/__init__.py` - Added templates_router export
- `app/main.py` - Registered templates router
- `frontend/src/components/settings/index.ts` - Added TemplateUpload export
- `frontend/src/pages/Settings.tsx` - Added Branding tab
