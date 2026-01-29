/**
 * TypeScript interfaces for analysis types
 */

// Query types for datasets
export type QueryType = 'embedded_sql' | 'stored_procedure' | 'shared_dataset'

// Visual types
export type VisualType =
  | 'tablix'
  | 'table'
  | 'matrix'
  | 'chart'
  | 'gauge'
  | 'map'
  | 'subreport'
  | 'textbox'
  | 'image'
  | 'rectangle'
  | 'line'
  | 'list'

// Expression categories
export type ExpressionCategory =
  | 'field_reference'
  | 'simple_aggregate'
  | 'complex_aggregate'
  | 'lookup'
  | 'custom_code'
  | 'running_value'
  | 'row_number'
  | 'previous'
  | 'unknown'

// Expression conversion categories
export type ExpressionConversionCategory = 'auto' | 'partial' | 'manual'

// TODO item categories
export type TodoCategory =
  | 'stored_procedure'
  | 'expression'
  | 'subreport'
  | 'custom_code'
  | 'unsupported_visual'

// TODO priorities
export type TodoPriority = 'high' | 'medium' | 'low'

// Conversion status
export type ConversionStatus = 'green' | 'yellow' | 'red'

// Report classification
export type ReportClassification = 'Tabular' | 'Analytical' | 'Mixed' | 'Complex'

// Dataset parameter
export interface DatasetParameter {
  name: string
  data_type?: string
  default_value?: string
}

// Dataset field
export interface DatasetField {
  name: string
  data_type?: string
  source_field?: string
}

// Dataset feature
export interface DatasetFeature {
  name: string
  query_type: QueryType
  stored_procedure_name?: string
  command_text?: string
  data_source_name?: string
  parameter_count: number
  field_count: number
  parameters: DatasetParameter[]
  fields: DatasetField[]
}

// Grouping info
export interface GroupingInfo {
  name: string
  expression?: string
  is_recursive: boolean
}

// Visual feature
export interface VisualFeature {
  type: VisualType
  name: string
  dataset_name?: string
  row_groups: number
  column_groups: number
  has_recursive_group: boolean
  nested_item_count: number
  row_group_details: GroupingInfo[]
  column_group_details: GroupingInfo[]
  subreport_path?: string
}

// Expression feature
export interface ExpressionFeature {
  expression: string
  category: ExpressionCategory
  location: string
  item_name?: string
  function_calls: string[]
}

// Layout feature
export interface LayoutFeature {
  page_width?: string
  page_height?: string
  page_width_inches?: number
  page_height_inches?: number
  orientation: string
  has_header: boolean
  has_footer: boolean
  header_height?: string
  footer_height?: string
  column_count: number
  left_margin?: string
  right_margin?: string
  top_margin?: string
  bottom_margin?: string
}

// Custom code function
export interface CustomCodeFunction {
  name: string
  parameters: string[]
  is_public: boolean
  line_count: number
}

// Analysis features
export interface AnalysisFeatures {
  rdl_version: string
  report_name?: string
  report_description?: string
  author?: string
  datasets: DatasetFeature[]
  visuals: VisualFeature[]
  expressions: ExpressionFeature[]
  layout?: LayoutFeature
  custom_code?: string
  custom_code_functions: CustomCodeFunction[]
  report_parameters: DatasetParameter[]
  data_sources: string[]
  dataset_count: number
  stored_procedure_count: number
  visual_count: number
  expression_count: number
  subreport_count: number
  running_value_count: number
  custom_code_function_count: number
  parameter_count: number
  chart_count: number
  table_count: number
  matrix_count: number
  map_count: number
  gauge_count: number
  has_custom_code: boolean
  has_stored_procedures: boolean
  has_subreports: boolean
  has_recursive_groups: boolean
  has_lookup_expressions: boolean
  has_running_values: boolean
}

// Penalty item
export interface PenaltyItem {
  category: string
  item_name?: string
  penalty_percent: number
  reason: string
}

// Score breakdown
export interface ScoreBreakdown {
  base_score: number
  penalties: PenaltyItem[]
  final_score: number
}

// Code analysis expression
export interface ExpressionAnalysis {
  expression: string
  category: ExpressionConversionCategory
  location: string
  item_name?: string
  reason: string
  suggested_dax?: string
  pattern_matched?: string
}

// TODO item
export interface TodoItem {
  id: number
  analysis_id: number
  title: string
  category: TodoCategory
  priority: TodoPriority
  location: string
  item_name?: string
  guidance: string
  original_content?: string
  is_resolved: boolean
  resolved_at?: string
  resolved_by?: number
  created_at?: string
}

// TODO list summary
export interface TodoListSummary {
  total_count: number
  high_priority_count: number
  medium_priority_count: number
  low_priority_count: number
  resolved_count: number
  unresolved_count: number
  completion_percentage: number
}

// TODO list response
export interface TodoListResponse {
  items: TodoItem[]
  summary: TodoListSummary
  high_priority_items: TodoItem[]
  medium_priority_items: TodoItem[]
  low_priority_items: TodoItem[]
  by_category: Record<string, TodoItem[]>
}

// Empty TODO list response
export interface EmptyTodoListResponse {
  message: string
  can_proceed_to_conversion: boolean
  summary: TodoListSummary
}

// Full analysis result (extended from backend response)
export interface AnalysisResult {
  id: number
  report_path: string
  report_name: string
  analyzed_at: string
  classification: ReportClassification | null
  score: number | null
  status: ConversionStatus | null
  features: AnalysisFeatures | null
  penalties: ScoreBreakdown | null
  todo_items: TodoItem[] | null
  analysis_duration_ms: number | null
}

// Type guard for TODO list responses
export function isTodoListResponse(
  response: TodoListResponse | EmptyTodoListResponse
): response is TodoListResponse {
  return 'items' in response && Array.isArray(response.items)
}
