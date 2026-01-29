/**
 * TypeScript type definitions
 */

// API Response Types
export interface ApiResponse<T> {
  data: T
  meta?: {
    page?: number
    pageSize?: number
    totalCount?: number
  }
}

export interface ApiError {
  error: {
    code: string
    message: string
    details?: Record<string, unknown>
  }
}

// Health Check
export interface HealthResponse {
  status: 'healthy' | 'unhealthy'
  timestamp: string
  version: string
}

// User Types (placeholder for authentication)
export interface User {
  id: string
  username: string
  email: string
  displayName: string
  roles: string[]
}

// Report Types (placeholder for SSRS reports)
export interface Report {
  id: string
  name: string
  path: string
  description?: string
  createdDate: string
  modifiedDate: string
}

// Analysis Types (placeholder for report analysis)
export interface AnalysisResult {
  reportId: string
  score: number
  complexity: 'simple' | 'moderate' | 'complex'
  features: string[]
  todos: string[]
}
