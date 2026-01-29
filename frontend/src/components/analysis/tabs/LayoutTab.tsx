/**
 * Layout tab content for analysis features
 */

import { LayoutTemplate, CheckCircle, XCircle } from 'lucide-react'
import type { LayoutFeature } from '@/types/analysis'

interface LayoutTabProps {
  layout: LayoutFeature | null | undefined
}

function LayoutItem({
  label,
  value,
  isBoolean = false,
}: {
  label: string
  value: string | boolean | null | undefined
  isBoolean?: boolean
}) {
  if (isBoolean) {
    return (
      <div className="flex items-center justify-between py-2 border-b last:border-0">
        <span className="text-sm text-muted-foreground">{label}</span>
        {value ? (
          <div className="flex items-center gap-1 text-green-600">
            <CheckCircle className="h-4 w-4" />
            <span className="text-sm">Yes</span>
          </div>
        ) : (
          <div className="flex items-center gap-1 text-muted-foreground">
            <XCircle className="h-4 w-4" />
            <span className="text-sm">No</span>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="flex items-center justify-between py-2 border-b last:border-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{value || '-'}</span>
    </div>
  )
}

export function LayoutTab({ layout }: LayoutTabProps) {
  if (!layout) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center text-muted-foreground">
        <LayoutTemplate className="h-12 w-12 mb-4 opacity-50" />
        <p>No layout information available</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Page Settings */}
      <div className="space-y-2">
        <h4 className="font-medium text-sm uppercase text-muted-foreground">
          Page Settings
        </h4>
        <div className="bg-muted/50 rounded-lg p-4">
          <LayoutItem label="Orientation" value={layout.orientation} />
          <LayoutItem
            label="Page Size"
            value={
              layout.page_width && layout.page_height
                ? `${layout.page_width} x ${layout.page_height}`
                : null
            }
          />
          <LayoutItem label="Columns" value={layout.column_count.toString()} />
        </div>
      </div>

      {/* Margins */}
      <div className="space-y-2">
        <h4 className="font-medium text-sm uppercase text-muted-foreground">
          Margins
        </h4>
        <div className="bg-muted/50 rounded-lg p-4">
          <LayoutItem label="Left" value={layout.left_margin} />
          <LayoutItem label="Right" value={layout.right_margin} />
          <LayoutItem label="Top" value={layout.top_margin} />
          <LayoutItem label="Bottom" value={layout.bottom_margin} />
        </div>
      </div>

      {/* Header & Footer */}
      <div className="space-y-2">
        <h4 className="font-medium text-sm uppercase text-muted-foreground">
          Header & Footer
        </h4>
        <div className="bg-muted/50 rounded-lg p-4">
          <LayoutItem label="Has Header" value={layout.has_header} isBoolean />
          {layout.has_header && layout.header_height && (
            <LayoutItem label="Header Height" value={layout.header_height} />
          )}
          <LayoutItem label="Has Footer" value={layout.has_footer} isBoolean />
          {layout.has_footer && layout.footer_height && (
            <LayoutItem label="Footer Height" value={layout.footer_height} />
          )}
        </div>
      </div>

      {/* Visual Representation */}
      <div className="space-y-2">
        <h4 className="font-medium text-sm uppercase text-muted-foreground">
          Preview
        </h4>
        <div className="bg-muted/50 rounded-lg p-4 flex items-center justify-center">
          <div
            className={`border-2 border-dashed border-primary/50 bg-background flex flex-col ${
              layout.orientation === 'Landscape' ? 'w-40 h-28' : 'w-28 h-40'
            }`}
          >
            {layout.has_header && (
              <div className="h-4 bg-primary/20 border-b border-dashed border-primary/30" />
            )}
            <div className="flex-1 flex items-center justify-center text-xs text-muted-foreground">
              {layout.orientation}
            </div>
            {layout.has_footer && (
              <div className="h-4 bg-primary/20 border-t border-dashed border-primary/30" />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
