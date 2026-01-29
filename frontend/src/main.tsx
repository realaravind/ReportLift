import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import { Login } from './pages/Login'
import { Settings } from './pages/Settings'
import { OAuthCallback } from './pages/OAuthCallback'
import { OAuthError } from './pages/OAuthError'
import { AnalysisResults } from './pages/AnalysisResults'
import { ConversionSummary } from './pages/ConversionSummary'
import { AuditLogs } from './pages/AuditLogs'
import { UploadPage } from './pages/Upload'
import { ProtectedRoute } from './components/auth'
import { BaseLayout } from './components/layout'
import { Toaster } from './components/ui/sonner'
import { queryClient } from './lib/queryClient'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <Toaster />
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/oauth-callback" element={<OAuthCallback />} />
          <Route path="/oauth-error" element={<OAuthError />} />

          {/* Protected routes */}
          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <BaseLayout>
                  <Settings />
                </BaseLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/analysis/:analysisId"
            element={
              <ProtectedRoute>
                <BaseLayout>
                  <AnalysisResults />
                </BaseLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/conversion/:conversionId/summary"
            element={
              <ProtectedRoute>
                <BaseLayout>
                  <ConversionSummary />
                </BaseLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/audit"
            element={
              <ProtectedRoute>
                <BaseLayout>
                  <AuditLogs />
                </BaseLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/upload"
            element={
              <ProtectedRoute>
                <BaseLayout>
                  <UploadPage />
                </BaseLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <App />
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
