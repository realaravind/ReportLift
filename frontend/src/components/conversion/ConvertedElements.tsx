/**
 * ConvertedElements - Displays what was successfully converted
 */

import { CheckCircle, Database, BarChart, Code, FileCode } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { type ConvertedSummary } from '@/hooks/useConversion'

interface ConvertedElementsProps {
  converted: ConvertedSummary
  className?: string
}

interface StatItemProps {
  icon: React.ElementType
  label: string
  count: number
  total?: number
  description?: string
}

function StatItem({ icon: Icon, label, count, total, description }: StatItemProps) {
  const displayValue = total !== undefined ? `${count}/${total}` : count.toString()

  return (
    <div className="flex items-start gap-3 p-3 rounded-lg hover:bg-muted/50 transition-colors">
      <div className="p-2 bg-green-100 dark:bg-green-900/20 rounded-lg">
        <Icon className="h-4 w-4 text-green-600 dark:text-green-400" />
      </div>
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <CheckCircle className="h-4 w-4 text-green-600" />
          <span className="font-medium text-sm">{displayValue}</span>
          <span className="text-sm text-muted-foreground">{label}</span>
        </div>
        {description && (
          <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
        )}
      </div>
    </div>
  )
}

export function ConvertedElements({ converted, className }: ConvertedElementsProps) {
  const { datasets, visuals, expressions, stored_procedures } = converted

  // Calculate visual breakdown
  const convertedVisuals = visuals.tables + visuals.charts + visuals.matrices + visuals.textboxes
  const visualDetails = []
  if (visuals.tables > 0) visualDetails.push(`${visuals.tables} tables`)
  if (visuals.charts > 0) visualDetails.push(`${visuals.charts} charts`)
  if (visuals.matrices > 0) visualDetails.push(`${visuals.matrices} matrices`)
  if (visuals.textboxes > 0) visualDetails.push(`${visuals.textboxes} textboxes`)

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <CheckCircle className="h-5 w-5 text-green-600" />
          What Was Converted
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        {/* Datasets */}
        <StatItem
          icon={Database}
          label="Datasets converted to SQL"
          count={datasets.converted_to_sql}
          total={datasets.total}
        />

        {/* Visuals */}
        <StatItem
          icon={BarChart}
          label="Visuals converted"
          count={convertedVisuals}
          total={visuals.total}
          description={visualDetails.length > 0 ? visualDetails.join(', ') : undefined}
        />

        {/* Expressions */}
        {expressions.total > 0 && (
          <StatItem
            icon={Code}
            label="Expressions auto-converted"
            count={expressions.auto_converted}
            total={expressions.total}
          />
        )}

        {/* Stored Procedures */}
        {stored_procedures.total > 0 && (
          <StatItem
            icon={FileCode}
            label="Stored procedures auto-rewritten"
            count={stored_procedures.auto_rewritten + stored_procedures.partial_rewrite}
            total={stored_procedures.total}
            description={
              stored_procedures.partial_rewrite > 0
                ? `${stored_procedures.auto_rewritten} full, ${stored_procedures.partial_rewrite} partial`
                : undefined
            }
          />
        )}

        {/* Summary when everything is converted */}
        {datasets.converted_to_sql === datasets.total &&
          convertedVisuals === visuals.total &&
          expressions.auto_converted === expressions.total &&
          stored_procedures.auto_rewritten === stored_procedures.total && (
            <div className="mt-4 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
              <p className="text-sm text-green-700 dark:text-green-300 flex items-center gap-2">
                <CheckCircle className="h-4 w-4" />
                All elements were successfully converted!
              </p>
            </div>
          )}
      </CardContent>
    </Card>
  )
}

export default ConvertedElements
