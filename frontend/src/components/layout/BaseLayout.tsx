/**
 * BaseLayout Component - Simple layout with just header and main content
 *
 * Used for pages that don't need the SSRS browser sidebar (e.g., Settings).
 */

import { Header } from './Header'

interface BaseLayoutProps {
  children?: React.ReactNode
}

export function BaseLayout({ children }: BaseLayoutProps) {
  return (
    <div className="flex min-h-screen flex-col">
      {/* Fixed header */}
      <Header />

      {/* Main content area below header */}
      <main className="flex-1 pt-16 bg-background">
        {children}
      </main>
    </div>
  )
}

export default BaseLayout
