/**
 * Expressions tab content for analysis features
 */

import { useState } from 'react'
import { Code, Search } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import type { ExpressionFeature, ExpressionCategory } from '@/types/analysis'

interface ExpressionsTabProps {
  expressions: ExpressionFeature[]
}

function CategoryBadge({ category }: { category: ExpressionCategory }) {
  const variants: Record<ExpressionCategory, 'success' | 'warning' | 'danger' | 'secondary'> = {
    field_reference: 'success',
    simple_aggregate: 'success',
    complex_aggregate: 'warning',
    lookup: 'warning',
    custom_code: 'danger',
    running_value: 'warning',
    row_number: 'success',
    previous: 'warning',
    unknown: 'secondary',
  }

  const labels: Record<ExpressionCategory, string> = {
    field_reference: 'Field Reference',
    simple_aggregate: 'Simple Aggregate',
    complex_aggregate: 'Complex Aggregate',
    lookup: 'Lookup',
    custom_code: 'Custom Code',
    running_value: 'Running Value',
    row_number: 'Row Number',
    previous: 'Previous',
    unknown: 'Unknown',
  }

  return (
    <Badge variant={variants[category] || 'secondary'}>
      {labels[category] || category}
    </Badge>
  )
}

export function ExpressionsTab({ expressions }: ExpressionsTabProps) {
  const [filter, setFilter] = useState('')

  const filteredExpressions = expressions.filter(
    (expr) =>
      expr.expression.toLowerCase().includes(filter.toLowerCase()) ||
      expr.location.toLowerCase().includes(filter.toLowerCase()) ||
      expr.category.toLowerCase().includes(filter.toLowerCase())
  )

  if (expressions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center text-muted-foreground">
        <Code className="h-12 w-12 mb-4 opacity-50" />
        <p>No expressions found in this report</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Filter input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Filter expressions..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Stats */}
      <div className="flex gap-4 text-sm text-muted-foreground">
        <span>Total: {expressions.length}</span>
        {filter && <span>Showing: {filteredExpressions.length}</span>}
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Location</TableHead>
            <TableHead>Category</TableHead>
            <TableHead className="w-1/2">Expression</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {filteredExpressions.map((expr, index) => (
            <Collapsible key={index} asChild>
              <>
                <TableRow>
                  <TableCell>
                    <CollapsibleTrigger className="font-medium hover:underline cursor-pointer text-left">
                      {expr.item_name || expr.location}
                    </CollapsibleTrigger>
                    {expr.item_name && (
                      <p className="text-xs text-muted-foreground">{expr.location}</p>
                    )}
                  </TableCell>
                  <TableCell>
                    <CategoryBadge category={expr.category} />
                  </TableCell>
                  <TableCell>
                    <code className="text-xs bg-muted px-2 py-1 rounded block truncate max-w-md">
                      {expr.expression}
                    </code>
                  </TableCell>
                </TableRow>
                <CollapsibleContent asChild>
                  <TableRow className="bg-muted/50">
                    <TableCell colSpan={3} className="p-4">
                      <div className="space-y-4">
                        <div>
                          <span className="font-medium">Full Expression:</span>
                          <pre className="mt-1 p-3 bg-background rounded text-sm overflow-x-auto border">
                            {expr.expression}
                          </pre>
                        </div>
                        {expr.function_calls.length > 0 && (
                          <div>
                            <span className="font-medium">Function Calls:</span>
                            <div className="mt-1 flex flex-wrap gap-2">
                              {expr.function_calls.map((func, idx) => (
                                <code
                                  key={idx}
                                  className="text-sm bg-background px-2 py-1 rounded border"
                                >
                                  {func}()
                                </code>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                </CollapsibleContent>
              </>
            </Collapsible>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
