/**
 * AttentionItems - Displays items requiring user attention
 */

import { Link } from 'react-router-dom'
import { AlertTriangle, FileCode, BarChart, Code, ExternalLink, CheckCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { type AttentionItem, type ConvertedSummary } from '@/hooks/useConversion'

interface AttentionItemsProps {
  attentionItems: AttentionItem[]
  converted: ConvertedSummary
  todoCount: number
  analysisId: number
  className?: string
}

// Icon mapping for attention item types
const TypeIcons: Record<string, React.ElementType> = {
  stored_procedure: FileCode,
  visual: BarChart,
  expression: Code,
}

interface AttentionListItemProps {
  item: AttentionItem
}

function AttentionListItem({ item }: AttentionListItemProps) {
  const Icon = TypeIcons[item.type] || AlertTriangle

  return (
    <div className="flex items-start gap-3 p-3 rounded-lg hover:bg-muted/50 transition-colors border-l-2 border-yellow-400">
      <div className="p-2 bg-yellow-100 dark:bg-yellow-900/20 rounded-lg">
        <Icon className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
      </div>
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm">{item.name}</span>
          {item.visual_type && (
            <Badge variant="outline" className="text-xs">
              {item.visual_type}
            </Badge>
          )}
        </div>
        <p className="text-xs text-muted-foreground mt-0.5">{item.reason}</p>
      </div>
    </div>
  )
}

export function AttentionItems({
  attentionItems,
  converted,
  todoCount,
  analysisId,
  className,
}: AttentionItemsProps) {
  // Count items by type
  const spCount = converted.stored_procedures.manual_required
  const visualCount = converted.visuals.placeholders
  const exprCount = converted.expressions.manual_required

  // If no attention items, show success state
  if (attentionItems.length === 0 && spCount === 0 && visualCount === 0 && exprCount === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <CheckCircle className="h-5 w-5 text-green-600" />
            No Items Need Attention
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
            <p className="text-sm text-green-700 dark:text-green-300">
              All elements were converted without issues. You can proceed to use the generated files.
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <AlertTriangle className="h-5 w-5 text-yellow-600" />
          What Needs Attention
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Summary badges */}
        <div className="flex flex-wrap gap-2">
          {spCount > 0 && (
            <Badge variant="secondary" className="flex items-center gap-1">
              <FileCode className="h-3 w-3" />
              {spCount} Stored Procedure{spCount > 1 ? 's' : ''}
            </Badge>
          )}
          {visualCount > 0 && (
            <Badge variant="secondary" className="flex items-center gap-1">
              <BarChart className="h-3 w-3" />
              {visualCount} Unsupported Visual{visualCount > 1 ? 's' : ''}
            </Badge>
          )}
          {exprCount > 0 && (
            <Badge variant="secondary" className="flex items-center gap-1">
              <Code className="h-3 w-3" />
              {exprCount} Expression{exprCount > 1 ? 's' : ''} to Review
            </Badge>
          )}
        </div>

        {/* Attention items list */}
        {attentionItems.length > 0 && (
          <div className="space-y-2">
            {attentionItems.slice(0, 5).map((item, index) => (
              <AttentionListItem key={`${item.type}-${index}`} item={item} />
            ))}
            {attentionItems.length > 5 && (
              <p className="text-sm text-muted-foreground text-center py-2">
                And {attentionItems.length - 5} more item{attentionItems.length > 6 ? 's' : ''}...
              </p>
            )}
          </div>
        )}

        {/* Link to full TODO list */}
        {todoCount > 0 && (
          <div className="pt-2 border-t">
            <Button variant="outline" asChild className="w-full">
              <Link to={`/analysis/${analysisId}#todos`}>
                View Full TODO List ({todoCount} items)
                <ExternalLink className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
        )}

        {/* Help text */}
        <div className="p-3 bg-muted rounded-lg">
          <p className="text-xs text-muted-foreground">
            Items above may need manual review or modification. Check the generated SQL files
            and Power BI report for placeholder comments and TODO markers.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}

export default AttentionItems
