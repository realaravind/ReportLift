# Story 1.2: Split-Panel Explorer UI Shell

Status: done

## Story

As a **user**,
I want **a professional enterprise application layout with navigation and content panels**,
so that **I can efficiently browse SSRS folders and view report details**.

## Acceptance Criteria

### AC1: Split-Panel Layout Structure
**Given** the user is logged in
**When** they view the main application
**Then** a Split-Panel Explorer layout is displayed with:
  - A collapsible left panel (280px default width)
  - A content area (right panel) that fills remaining space
  - A header bar with application title "ReportLift"
  - A collapse/expand toggle for the left panel

### AC2: Panel Collapse Behavior
**Given** the left panel is expanded
**When** the user clicks the collapse toggle
**Then** the left panel collapses to a minimal width (icons only)
**And** the content area expands to fill the space
**And** the collapse state persists across page navigation

### AC3: Responsive Behavior
**Given** the application is viewed on different screen sizes
**When** viewed on screens >= 1024px
**Then** both panels are visible
**When** viewed on screens < 1024px
**Then** the left panel overlays content as a drawer

## Tasks / Subtasks

- [x] **Task 1: Create Layout Component Structure** (AC: 1)
  - [x] Create `frontend/src/components/layout/` directory
  - [x] Create `SplitPanel.tsx` - Main layout wrapper component
  - [x] Create `Header.tsx` - Top header bar with logo and user actions
  - [x] Create `Sidebar.tsx` - Left panel container component
  - [x] Create `MainContent.tsx` - Right panel content wrapper

- [x] **Task 2: Implement Header Component** (AC: 1)
  - [x] Add ReportLift logo/title in header left section
  - [x] Add Settings navigation link
  - [x] Add User menu/avatar placeholder (for auth integration)
  - [x] Style with Tailwind CSS matching enterprise aesthetic
  - [x] Ensure header is fixed/sticky at top

- [x] **Task 3: Implement Split-Panel Layout** (AC: 1, 2)
  - [x] Create flex container with left panel (280px) and right panel (flex-1)
  - [x] Add collapse/expand toggle button with icon (chevron)
  - [x] Implement collapsed state (60px width, icons only)
  - [x] Add smooth CSS transition for panel width changes
  - [x] Use Zustand store to manage collapse state
  - [x] Persist collapse state to localStorage

- [x] **Task 4: Implement Responsive Drawer Behavior** (AC: 3)
  - [x] Add media query breakpoint at 1024px
  - [x] Implement overlay drawer using shadcn/ui Sheet component
  - [x] Add hamburger menu button for mobile view
  - [x] Ensure drawer closes on navigation or outside click
  - [x] Test on various viewport sizes

- [x] **Task 5: Create Placeholder Content Components** (AC: 1)
  - [x] Create placeholder for folder tree area in left panel
  - [x] Create placeholder for report details area in right panel
  - [x] Add "Select a report to view details" empty state
  - [x] Style placeholders with appropriate messaging

- [x] **Task 6: Integrate with App Router** (AC: 1, 2)
  - [x] Wrap main routes with SplitPanel layout
  - [x] Ensure layout persists across route changes
  - [x] Verify collapse state survives navigation
  - [x] Add proper route structure for future pages

- [x] **Task 7: Verify All Acceptance Criteria** (AC: 1, 2, 3)
  - [x] Verify split-panel renders correctly at 280px/flex-1
  - [x] Verify collapse toggle works and state persists
  - [x] Verify responsive behavior at breakpoints
  - [x] Verify header displays correctly
  - [x] Test in Chrome and Edge browsers

## Dev Notes

### Architecture References

**UX Decision (from architecture.md):**
```
Split-Panel Explorer Layout
- Matches developer mental model (familiar file explorer / IDE pattern)
- Efficient workflow - click report, see details instantly
- Professional enterprise aesthetic
```

**Layout Structure:**
```
+-------------------------------------------------------------+
|  Header: ReportLift logo + Settings + User                   |
+----------------------+--------------------------------------+
|  Left Panel          |  Right Panel                          |
|  - SSRS Browser      |  - Report Details                     |
|  - Folder tree       |  - Analysis Score                     |
|  - Connection status |  - Classification & Datasets          |
|                      |  - TODO List                          |
|                      |  - Action Buttons (Analyze/Convert)   |
+----------------------+--------------------------------------+
```

### Technology Stack

| Component | Technology |
|-----------|------------|
| Layout Components | React 18 + TypeScript |
| Styling | Tailwind CSS |
| UI Components | shadcn/ui (Sheet for drawer) |
| State Management | Zustand (for collapse state) |
| Icons | Lucide React |

### shadcn/ui Components Required

Install/configure these shadcn/ui components:
- `Sheet` - For responsive drawer behavior
- `Button` - For toggle buttons
- `Separator` - For visual dividers

```bash
npx shadcn-ui@latest add sheet button separator
```

### Component Structure

```
frontend/src/components/layout/
+-- Header.tsx          # Fixed header with logo, settings, user
+-- SplitPanel.tsx      # Main layout wrapper
+-- Sidebar.tsx         # Left panel (collapsible)
+-- MainContent.tsx     # Right panel content area
```

### Zustand Store for UI State

```typescript
// frontend/src/store/uiStore.ts
interface UIState {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
}
```

### CSS Specifications

| Element | Specification |
|---------|--------------|
| Left Panel (expanded) | 280px width |
| Left Panel (collapsed) | 60px width (icons only) |
| Header Height | 64px |
| Transition | 200ms ease-in-out |
| Mobile Breakpoint | < 1024px |

### Browser Support

- Chrome (latest stable) - Full support required
- Edge (latest stable) - Full support required
- IE11 - Graceful degradation (basic layout, no transitions)

### Related Stories

- Story 1.1: Provides the base project structure and Zustand setup
- Story 1.3: Will add user authentication display to header
- Story 3.1: Will populate left panel with SSRS folder tree
- Story 3.2: Will populate right panel with report list

### References

- [Source: architecture.md#UX Architecture Decision] - Layout decision and rationale
- [Source: architecture.md#Frontend Organization] - Component structure patterns
- [Source: epics.md#Story 1.2] - Story requirements and acceptance criteria
- ARCH5: Split-Panel Explorer UI layout
- NFR24-26: Chrome, Edge, IE11 browser support

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List
- Created complete layout component structure with Header, Sidebar, MainContent, and SplitPanel components
- Implemented responsive sidebar: 280px expanded, 60px collapsed, with smooth CSS transitions
- Added Zustand store with localStorage persistence for collapse state
- Integrated shadcn/ui Sheet component for mobile drawer behavior at <1024px breakpoint
- Created UI components: Button, Separator, Sheet from shadcn/ui patterns
- Added hamburger menu button in header for mobile view
- Implemented empty state placeholder "Select a report to view details"
- Added vite-env.d.ts for TypeScript import.meta.env support
- Created ESLint configuration for React + TypeScript
- All acceptance criteria verified: layout renders correctly, collapse persists, responsive drawer works

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-22 | Created layout component structure | frontend/src/components/layout/*.tsx |
| 2026-01-22 | Added shadcn/ui components | frontend/src/components/ui/*.tsx |
| 2026-01-22 | Created UI store with persistence | frontend/src/store/uiStore.ts |
| 2026-01-22 | Updated App.tsx to use SplitPanel | frontend/src/App.tsx |
| 2026-01-22 | Added Radix UI dependencies | frontend/package.json |
| 2026-01-22 | Added TypeScript and ESLint config | frontend/tsconfig.json, .eslintrc.cjs |

### File List
- frontend/src/components/layout/Header.tsx
- frontend/src/components/layout/Sidebar.tsx
- frontend/src/components/layout/MainContent.tsx
- frontend/src/components/layout/SplitPanel.tsx
- frontend/src/components/layout/index.ts
- frontend/src/components/ui/button.tsx
- frontend/src/components/ui/separator.tsx
- frontend/src/components/ui/sheet.tsx
- frontend/src/store/uiStore.ts
- frontend/src/vite-env.d.ts
- frontend/.eslintrc.cjs
- frontend/tsconfig.json (updated)
- frontend/package.json (updated)
- frontend/src/App.tsx (updated)
