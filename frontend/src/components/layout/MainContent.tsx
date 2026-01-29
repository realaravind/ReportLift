/**
 * MainContent Component - Right panel content area
 */

import { FileText } from 'lucide-react'
import { cn } from '@/lib/utils'

interface MainContentProps {
  children?: React.ReactNode
  className?: string
}

export function MainContent({ children, className }: MainContentProps) {
  return (
    <main
      className={cn(
        'flex-1 overflow-auto bg-background p-6',
        className
      )}
    >
      {children || <EmptyState />}
    </main>
  )
}

function EmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center text-center">
      <div className="rounded-full bg-muted p-6 mb-4">
        <FileText className="h-12 w-12 text-muted-foreground" />
      </div>
      <h2 className="text-xl font-semibold mb-2">Select a report to view details</h2>
      <p className="text-muted-foreground max-w-md">
        Browse the SSRS folder tree on the left to find and select a report.
        Report details, analysis scores, and conversion options will appear here.
      </p>
    </div>
  )
}
