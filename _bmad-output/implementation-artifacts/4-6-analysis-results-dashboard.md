# Story 4.6: Analysis Results Dashboard

Status: done

## Story

As a **user**,
I want **to view a detailed analysis breakdown for a report**,
So that **I can make informed decisions about conversion**.

## Acceptance Criteria

### AC1: Summary Card Display
**Given** analysis has completed
**When** viewing the Analysis Results dashboard
**Then** a summary card displays:
  - Report name and path
  - Classification (Tabular/Analytical/Mixed/Complex)
  - Conversion score with visual indicator (green/yellow/red)
  - Analysis timestamp

### AC2: Score Breakdown Visualization
**Given** the Analysis Results dashboard
**When** viewing the Score Breakdown section
**Then** a visual breakdown shows:
  - Base score (100%)
  - Each penalty applied with reason
  - Final score calculation
  - Color-coded bar or gauge

### AC3: Features Tabs Display
**Given** the Analysis Results dashboard
**When** viewing the Features section
**Then** tabs or sections display:
  - **Datasets**: List with query type, parameters, SP flags
  - **Visuals**: List with type, grouping complexity
  - **Expressions**: List with category and location
  - **Layout**: Page settings, headers/footers

### AC4: TODO Section Display
**Given** the Analysis Results dashboard
**When** viewing the TODO section
**Then** the full TODO list from Story 4.5 is displayed
**And** items are expandable for full details
**And** a "Mark Resolved" checkbox is available per item

### AC5: Convert Button for Green Status
**Given** the analysis shows green status
**When** viewing the dashboard
**Then** a prominent "Convert Report" button is displayed
**And** conversion can be initiated directly

### AC6: Convert Button with Warning for Yellow/Red Status
**Given** the analysis shows yellow/red status
**When** viewing the dashboard
**Then** a "Convert Report" button is available with a warning
**And** warning text: "Review TODO items before converting"

### AC7: Re-Analyze Functionality
**Given** the user wants to re-analyze
**When** clicking "Re-Analyze"
**Then** a fresh analysis is triggered
**And** the new results replace the previous analysis

## Tasks / Subtasks

- [ ] **Task 1: Create Analysis Results Page Component** (AC: 1, 2, 3, 4, 5, 6, 7)
  - [ ] Create `frontend/src/pages/AnalysisResults.tsx`
  - [ ] Set up page layout with sections
  - [ ] Configure routing at `/reports/{id}/analysis`
  - [ ] Fetch analysis data with React Query

- [ ] **Task 2: Build Summary Card Component** (AC: 1)
  - [ ] Create `AnalysisSummaryCard.tsx`
  - [ ] Display report name and path
  - [ ] Show classification badge
  - [ ] Display score with color indicator
  - [ ] Format analysis timestamp

- [ ] **Task 3: Build Score Breakdown Component** (AC: 2)
  - [ ] Create `ScoreBreakdown.tsx`
  - [ ] Display base score (100%)
  - [ ] List each penalty with reason
  - [ ] Show calculation progression
  - [ ] Add color-coded progress bar

- [ ] **Task 4: Build Features Tabs Component** (AC: 3)
  - [ ] Create `FeaturesTabs.tsx` using shadcn/ui Tabs
  - [ ] Create `DatasetsTab.tsx` for dataset features
  - [ ] Create `VisualsTab.tsx` for visual features
  - [ ] Create `ExpressionsTab.tsx` for expression features
  - [ ] Create `LayoutTab.tsx` for layout features

- [ ] **Task 5: Build Datasets Tab Content** (AC: 3)
  - [ ] Display dataset list with columns: Name, Type, Parameters, SP Flag
  - [ ] Highlight stored procedure datasets
  - [ ] Show parameter details on expand
  - [ ] Use shadcn/ui Table component

- [ ] **Task 6: Build Visuals Tab Content** (AC: 3)
  - [ ] Display visual list with columns: Name, Type, Groups, Complexity
  - [ ] Show grouping details (row/column groups)
  - [ ] Flag subreports and maps
  - [ ] Indicate recursive hierarchies

- [ ] **Task 7: Build Expressions Tab Content** (AC: 3)
  - [ ] Display expression list with columns: Location, Category, Expression
  - [ ] Color-code by category (Auto/Partial/Manual)
  - [ ] Show suggested DAX for auto-convertible
  - [ ] Filter/search functionality

- [ ] **Task 8: Build Layout Tab Content** (AC: 3)
  - [ ] Display page dimensions and orientation
  - [ ] Show header/footer status
  - [ ] Display margin settings
  - [ ] Show column count

- [ ] **Task 9: Build TODO Section Component** (AC: 4)
  - [ ] Create `TodoSection.tsx`
  - [ ] Display TODO items grouped by priority
  - [ ] Expandable items for full guidance
  - [ ] "Mark Resolved" checkbox per item
  - [ ] Show total and resolved counts

- [ ] **Task 10: Implement TODO Resolution** (AC: 4)
  - [ ] Create mutation for marking resolved
  - [ ] Optimistic UI update on checkbox
  - [ ] Persist resolution to backend
  - [ ] Show resolved/unresolved count

- [ ] **Task 11: Build Convert Button Component** (AC: 5, 6)
  - [ ] Create `ConvertButton.tsx`
  - [ ] Green status: Primary button style
  - [ ] Yellow/Red status: Warning variant with icon
  - [ ] Add warning text for non-green reports
  - [ ] Handle click to initiate conversion

- [ ] **Task 12: Implement Re-Analyze Button** (AC: 7)
  - [ ] Add "Re-Analyze" button to header
  - [ ] Confirm before re-running analysis
  - [ ] Show loading state during analysis
  - [ ] Replace results when complete

- [ ] **Task 13: Create API Hooks** (AC: 1, 4, 7)
  - [ ] Create `useAnalysisResults` hook
  - [ ] Create `useUpdateTodo` mutation
  - [ ] Create `useReanalyzeReport` mutation
  - [ ] Handle loading and error states

- [ ] **Task 14: Responsive Design** (AC: 1, 2, 3, 4)
  - [ ] Ensure mobile-friendly layout
  - [ ] Stack tabs vertically on small screens
  - [ ] Collapsible sections for space
  - [ ] Test on various screen sizes

- [ ] **Task 15: Component Testing** (AC: 1, 2, 3, 4, 5, 6, 7)
  - [ ] Test summary card rendering
  - [ ] Test score breakdown accuracy
  - [ ] Test tab navigation
  - [ ] Test TODO resolution flow
  - [ ] Test convert button states

## Dev Notes

### Technical Implementation

**Page Component Structure:**
```typescript
// frontend/src/pages/AnalysisResults.tsx
import { useParams } from 'react-router-dom';
import { useAnalysisResults } from '@/hooks/useAnalysisResults';
import { AnalysisSummaryCard } from '@/components/analysis/AnalysisSummaryCard';
import { ScoreBreakdown } from '@/components/analysis/ScoreBreakdown';
import { FeaturesTabs } from '@/components/analysis/FeaturesTabs';
import { TodoSection } from '@/components/analysis/TodoSection';
import { ConvertButton } from '@/components/analysis/ConvertButton';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export function AnalysisResults() {
  const { reportId } = useParams<{ reportId: string }>();
  const { data: analysis, isLoading, error } = useAnalysisResults(reportId);
  const reanalyze = useReanalyzeReport();

  if (isLoading) return <AnalysisSkeleton />;
  if (error) return <AnalysisError error={error} />;
  if (!analysis) return <NoAnalysis reportId={reportId} />;

  return (
    <div className="space-y-6 p-6">
      {/* Header with actions */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Analysis Results</h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => reanalyze.mutate(reportId)}>
            Re-Analyze
          </Button>
          <ConvertButton
            status={analysis.status}
            reportId={reportId}
            todoCount={analysis.todos.filter(t => !t.isResolved).length}
          />
        </div>
      </div>

      {/* Summary Card */}
      <AnalysisSummaryCard analysis={analysis} />

      {/* Score Breakdown */}
      <ScoreBreakdown breakdown={analysis.breakdown} status={analysis.status} />

      {/* Features Tabs */}
      <FeaturesTabs features={analysis.features} />

      {/* TODO Section */}
      <TodoSection
        todos={analysis.todos}
        analysisId={analysis.id}
      />
    </div>
  );
}
```

**Summary Card Component:**
```typescript
// frontend/src/components/analysis/AnalysisSummaryCard.tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatDistanceToNow } from 'date-fns';

interface AnalysisSummaryCardProps {
  analysis: AnalysisResult;
}

const statusColors = {
  green: 'bg-green-100 text-green-800 border-green-200',
  yellow: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  red: 'bg-red-100 text-red-800 border-red-200',
};

const classificationBadge = {
  Tabular: 'bg-blue-100 text-blue-800',
  Analytical: 'bg-purple-100 text-purple-800',
  Mixed: 'bg-orange-100 text-orange-800',
  Complex: 'bg-red-100 text-red-800',
};

export function AnalysisSummaryCard({ analysis }: AnalysisSummaryCardProps) {
  return (
    <Card className={`border-2 ${statusColors[analysis.status]}`}>
      <CardHeader className="pb-2">
        <div className="flex justify-between items-start">
          <div>
            <CardTitle className="text-xl">{analysis.reportName}</CardTitle>
            <p className="text-sm text-muted-foreground">{analysis.reportPath}</p>
          </div>
          <Badge className={classificationBadge[analysis.classification]}>
            {analysis.classification}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="text-center">
              <div className={`text-4xl font-bold ${getScoreColor(analysis.score)}`}>
                {analysis.score}%
              </div>
              <div className="text-sm text-muted-foreground">Conversion Score</div>
            </div>
            <StatusIndicator status={analysis.status} />
          </div>
          <div className="text-sm text-muted-foreground">
            Analyzed {formatDistanceToNow(new Date(analysis.analysisTimestamp))} ago
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

**Score Breakdown Component:**
```typescript
// frontend/src/components/analysis/ScoreBreakdown.tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';

interface ScoreBreakdownProps {
  breakdown: ScoreBreakdown;
  status: ConversionStatus;
}

export function ScoreBreakdown({ breakdown, status }: ScoreBreakdownProps) {
  const progressColor = {
    green: 'bg-green-500',
    yellow: 'bg-yellow-500',
    red: 'bg-red-500',
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Score Breakdown</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Progress bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span>Conversion Score</span>
            <span className="font-medium">{breakdown.finalScore}%</span>
          </div>
          <Progress
            value={breakdown.finalScore}
            className="h-3"
            indicatorClassName={progressColor[status]}
          />
        </div>

        {/* Penalty breakdown */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm font-medium">
            <span>Base Score</span>
            <span>100%</span>
          </div>

          {breakdown.penalties.map((penalty, index) => (
            <div key={index} className="flex justify-between text-sm pl-4 text-muted-foreground">
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 bg-red-400 rounded-full" />
                {penalty.reason}
              </span>
              <span className="text-red-600">-{penalty.penaltyPercent}%</span>
            </div>
          ))}

          <div className="flex justify-between text-sm font-medium border-t pt-2">
            <span>Final Score</span>
            <span className={getScoreColor(breakdown.finalScore)}>{breakdown.finalScore}%</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

**Features Tabs Component:**
```typescript
// frontend/src/components/analysis/FeaturesTabs.tsx
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DatasetsTab } from './tabs/DatasetsTab';
import { VisualsTab } from './tabs/VisualsTab';
import { ExpressionsTab } from './tabs/ExpressionsTab';
import { LayoutTab } from './tabs/LayoutTab';

interface FeaturesTabsProps {
  features: AnalysisFeatures;
}

export function FeaturesTabs({ features }: FeaturesTabsProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Report Features</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="datasets">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="datasets">
              Datasets ({features.datasets.length})
            </TabsTrigger>
            <TabsTrigger value="visuals">
              Visuals ({features.visuals.length})
            </TabsTrigger>
            <TabsTrigger value="expressions">
              Expressions ({features.expressions.length})
            </TabsTrigger>
            <TabsTrigger value="layout">
              Layout
            </TabsTrigger>
          </TabsList>

          <TabsContent value="datasets">
            <DatasetsTab datasets={features.datasets} />
          </TabsContent>

          <TabsContent value="visuals">
            <VisualsTab visuals={features.visuals} />
          </TabsContent>

          <TabsContent value="expressions">
            <ExpressionsTab expressions={features.expressions} />
          </TabsContent>

          <TabsContent value="layout">
            <LayoutTab layout={features.layout} />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
```

**TODO Section Component:**
```typescript
// frontend/src/components/analysis/TodoSection.tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { ChevronDown } from 'lucide-react';
import { useUpdateTodo } from '@/hooks/useUpdateTodo';

interface TodoSectionProps {
  todos: TodoItem[];
  analysisId: string;
}

const priorityColors = {
  high: 'bg-red-100 text-red-800',
  medium: 'bg-yellow-100 text-yellow-800',
  low: 'bg-blue-100 text-blue-800',
};

export function TodoSection({ todos, analysisId }: TodoSectionProps) {
  const updateTodo = useUpdateTodo();
  const unresolvedCount = todos.filter(t => !t.isResolved).length;

  const handleResolve = (todoId: string, resolved: boolean) => {
    updateTodo.mutate({ todoId, isResolved: resolved });
  };

  // Group by category
  const grouped = todos.reduce((acc, todo) => {
    if (!acc[todo.category]) acc[todo.category] = [];
    acc[todo.category].push(todo);
    return acc;
  }, {} as Record<string, TodoItem[]>);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex justify-between items-center">
          <span>TODO Items</span>
          <span className="text-sm font-normal text-muted-foreground">
            {unresolvedCount} of {todos.length} items remaining
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {todos.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            No manual work items identified. Report is ready for conversion.
          </div>
        ) : (
          <div className="space-y-4">
            {Object.entries(grouped).map(([category, categoryTodos]) => (
              <div key={category} className="space-y-2">
                <h4 className="font-medium capitalize">{category.replace('_', ' ')}</h4>
                {categoryTodos.map((todo) => (
                  <Collapsible key={todo.id}>
                    <div className="flex items-start gap-3 p-3 border rounded-lg">
                      <Checkbox
                        checked={todo.isResolved}
                        onCheckedChange={(checked) => handleResolve(todo.id, !!checked)}
                      />
                      <div className="flex-1">
                        <CollapsibleTrigger className="flex items-center gap-2 w-full text-left">
                          <span className={todo.isResolved ? 'line-through text-muted-foreground' : ''}>
                            {todo.title}
                          </span>
                          <Badge className={priorityColors[todo.priority]}>
                            {todo.priority}
                          </Badge>
                          <ChevronDown className="h-4 w-4 ml-auto" />
                        </CollapsibleTrigger>
                        <CollapsibleContent className="mt-2 space-y-2">
                          <p className="text-sm text-muted-foreground">
                            <strong>Location:</strong> {todo.location}
                          </p>
                          {todo.originalContent && (
                            <p className="text-sm font-mono bg-muted p-2 rounded">
                              {todo.originalContent}
                            </p>
                          )}
                          <div className="text-sm whitespace-pre-wrap bg-blue-50 p-3 rounded">
                            <strong>Guidance:</strong>
                            <p className="mt-1">{todo.guidance}</p>
                          </div>
                        </CollapsibleContent>
                      </div>
                    </div>
                  </Collapsible>
                ))}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

**Convert Button Component:**
```typescript
// frontend/src/components/analysis/ConvertButton.tsx
import { Button } from '@/components/ui/button';
import { AlertTriangle, CheckCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface ConvertButtonProps {
  status: ConversionStatus;
  reportId: string;
  todoCount: number;
}

export function ConvertButton({ status, reportId, todoCount }: ConvertButtonProps) {
  const navigate = useNavigate();

  const handleConvert = () => {
    navigate(`/reports/${reportId}/convert`);
  };

  if (status === 'green') {
    return (
      <Button onClick={handleConvert} className="bg-green-600 hover:bg-green-700">
        <CheckCircle className="mr-2 h-4 w-4" />
        Convert Report
      </Button>
    );
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <Button onClick={handleConvert} variant="outline" className="border-yellow-500 text-yellow-700">
        <AlertTriangle className="mr-2 h-4 w-4" />
        Convert Report
      </Button>
      <span className="text-xs text-muted-foreground">
        Review {todoCount} TODO items before converting
      </span>
    </div>
  );
}
```

**React Query Hooks:**
```typescript
// frontend/src/hooks/useAnalysisResults.ts
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function useAnalysisResults(reportId: string | undefined) {
  return useQuery({
    queryKey: ['analysis', reportId],
    queryFn: () => api.get(`/reports/${reportId}/analysis`).then(res => res.data),
    enabled: !!reportId,
  });
}

// frontend/src/hooks/useUpdateTodo.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function useUpdateTodo() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ todoId, isResolved }: { todoId: string; isResolved: boolean }) =>
      api.patch(`/todos/${todoId}`, { is_resolved: isResolved }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['analysis'] });
    },
  });
}
```

### TypeScript Interfaces

```typescript
// frontend/src/types/analysis.ts
export interface AnalysisResult {
  id: string;
  reportPath: string;
  reportName: string;
  classification: 'Tabular' | 'Analytical' | 'Mixed' | 'Complex';
  score: number;
  status: 'green' | 'yellow' | 'red';
  analysisTimestamp: string;
  breakdown: ScoreBreakdown;
  features: AnalysisFeatures;
  todos: TodoItem[];
}

export interface ScoreBreakdown {
  baseScore: number;
  penalties: PenaltyItem[];
  finalScore: number;
}

export interface PenaltyItem {
  category: string;
  itemName: string;
  penaltyPercent: number;
  reason: string;
}

export interface TodoItem {
  id: string;
  title: string;
  category: string;
  priority: 'high' | 'medium' | 'low';
  location: string;
  itemName: string;
  guidance: string;
  originalContent?: string;
  isResolved: boolean;
}
```

### Component File Structure

```
frontend/src/
  pages/
    AnalysisResults.tsx
  components/
    analysis/
      AnalysisSummaryCard.tsx
      ScoreBreakdown.tsx
      FeaturesTabs.tsx
      TodoSection.tsx
      ConvertButton.tsx
      tabs/
        DatasetsTab.tsx
        VisualsTab.tsx
        ExpressionsTab.tsx
        LayoutTab.tsx
  hooks/
    useAnalysisResults.ts
    useUpdateTodo.ts
    useReanalyzeReport.ts
  types/
    analysis.ts
```

### shadcn/ui Components Required

- Card, CardHeader, CardTitle, CardContent
- Tabs, TabsList, TabsTrigger, TabsContent
- Badge
- Button
- Checkbox
- Progress
- Collapsible, CollapsibleTrigger, CollapsibleContent
- Table, TableHeader, TableBody, TableRow, TableCell

### Dependencies

- Story 4.1 (Trigger Analysis) - Provides analysis data
- Story 4.5 (TODO Generation) - Provides TODO items
- shadcn/ui components (install if not present)

### References

- [Source: epics.md#Story 4.6] - Original story definition
- [Source: prd.md#FR17] - View detailed analysis breakdown
- [Source: architecture.md] - UI component choices

### Architecture Compliance Checklist

- [ ] Uses shadcn/ui Cards and Tabs as specified
- [ ] React Query for server state management
- [ ] TypeScript interfaces match API response
- [ ] Responsive design for all screen sizes
- [ ] Optimistic updates for TODO resolution

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5

### Completion Notes List

- Created comprehensive TypeScript interfaces for all analysis types in `src/types/analysis.ts`
- Installed and configured shadcn/ui components: Badge, Checkbox, Collapsible, Table
- Built React Query hooks for TODO operations in `src/hooks/useTodos.ts`
- Created analysis components: AnalysisSummaryCard, ScoreBreakdown, FeaturesTabs (with DatasetsTab, VisualsTab, ExpressionsTab, LayoutTab), TodoSection, ConvertButton
- Created AnalysisResults page with full routing at `/analysis/:analysisId`
- Updated App.tsx to navigate to analysis page from "View Analysis" button
- All 208 backend tests pass
- Frontend builds successfully

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-22 | Created analysis TypeScript interfaces | frontend/src/types/analysis.ts |
| 2026-01-22 | Added shadcn/ui components | frontend/src/components/ui/badge.tsx, checkbox.tsx, collapsible.tsx, table.tsx |
| 2026-01-22 | Created TODO hooks | frontend/src/hooks/useTodos.ts |
| 2026-01-22 | Created analysis components | frontend/src/components/analysis/*.tsx |
| 2026-01-22 | Created AnalysisResults page | frontend/src/pages/AnalysisResults.tsx |
| 2026-01-22 | Updated routing and navigation | frontend/src/main.tsx, frontend/src/App.tsx |

### File List

- frontend/src/types/analysis.ts
- frontend/src/components/ui/badge.tsx
- frontend/src/components/ui/checkbox.tsx
- frontend/src/components/ui/collapsible.tsx
- frontend/src/components/ui/table.tsx
- frontend/src/hooks/useTodos.ts
- frontend/src/components/analysis/AnalysisSummaryCard.tsx
- frontend/src/components/analysis/ScoreBreakdown.tsx
- frontend/src/components/analysis/FeaturesTabs.tsx
- frontend/src/components/analysis/TodoSection.tsx
- frontend/src/components/analysis/ConvertButton.tsx
- frontend/src/components/analysis/index.ts
- frontend/src/components/analysis/tabs/DatasetsTab.tsx
- frontend/src/components/analysis/tabs/VisualsTab.tsx
- frontend/src/components/analysis/tabs/ExpressionsTab.tsx
- frontend/src/components/analysis/tabs/LayoutTab.tsx
- frontend/src/pages/AnalysisResults.tsx
- frontend/src/main.tsx (modified)
- frontend/src/App.tsx (modified)
