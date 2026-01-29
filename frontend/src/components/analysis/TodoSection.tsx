/**
 * TODO section component for analysis display
 */

import { useState } from 'react'
import { ChevronDown, CheckSquare, AlertTriangle, Info, Clock } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { useUpdateTodo } from '@/hooks/useTodos'
import type { TodoItem, TodoPriority, TodoCategory } from '@/types/analysis'
import { cn } from '@/lib/utils'

interface TodoSectionProps {
  todos: TodoItem[]
  analysisId?: number
}

const priorityConfig: Record<
  TodoPriority,
  { variant: 'danger' | 'warning' | 'secondary'; icon: typeof AlertTriangle }
> = {
  high: { variant: 'danger', icon: AlertTriangle },
  medium: { variant: 'warning', icon: Clock },
  low: { variant: 'secondary', icon: Info },
}

const categoryLabels: Record<TodoCategory, string> = {
  stored_procedure: 'Stored Procedures',
  expression: 'Expressions',
  subreport: 'Subreports',
  custom_code: 'Custom Code',
  unsupported_visual: 'Unsupported Visuals',
}

function TodoItemCard({
  todo,
  onResolve,
}: {
  todo: TodoItem
  onResolve: (resolved: boolean) => void
}) {
  const [isOpen, setIsOpen] = useState(false)
  const PriorityIcon = priorityConfig[todo.priority].icon

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <div
        className={cn(
          'flex items-start gap-3 p-3 border rounded-lg transition-colors',
          todo.is_resolved && 'bg-muted/50'
        )}
      >
        <Checkbox
          checked={todo.is_resolved}
          onCheckedChange={(checked) => onResolve(!!checked)}
          className="mt-1"
        />
        <div className="flex-1 min-w-0">
          <CollapsibleTrigger className="flex items-center gap-2 w-full text-left group">
            <span
              className={cn(
                'flex-1',
                todo.is_resolved && 'line-through text-muted-foreground'
              )}
            >
              {todo.title}
            </span>
            <Badge variant={priorityConfig[todo.priority].variant} className="flex-shrink-0">
              <PriorityIcon className="h-3 w-3 mr-1" />
              {todo.priority}
            </Badge>
            <ChevronDown
              className={cn(
                'h-4 w-4 text-muted-foreground transition-transform',
                isOpen && 'rotate-180'
              )}
            />
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-3 space-y-3">
            <div className="text-sm">
              <span className="font-medium text-muted-foreground">Location: </span>
              {todo.location}
            </div>
            {todo.item_name && (
              <div className="text-sm">
                <span className="font-medium text-muted-foreground">Item: </span>
                <code className="bg-muted px-1 rounded">{todo.item_name}</code>
              </div>
            )}
            {todo.original_content && (
              <div className="space-y-1">
                <span className="text-sm font-medium text-muted-foreground">
                  Original Content:
                </span>
                <pre className="text-xs font-mono bg-muted p-2 rounded overflow-x-auto">
                  {todo.original_content}
                </pre>
              </div>
            )}
            <div className="space-y-1">
              <span className="text-sm font-medium text-muted-foreground">
                Guidance:
              </span>
              <div className="text-sm bg-blue-50 dark:bg-blue-950 p-3 rounded border border-blue-200 dark:border-blue-800">
                {todo.guidance}
              </div>
            </div>
          </CollapsibleContent>
        </div>
      </div>
    </Collapsible>
  )
}

export function TodoSection({ todos }: TodoSectionProps) {
  const updateTodo = useUpdateTodo()

  const handleResolve = (todoId: number, isResolved: boolean) => {
    updateTodo.mutate({ todoId, isResolved })
  }

  const unresolvedCount = todos.filter((t) => !t.is_resolved).length
  const resolvedCount = todos.filter((t) => t.is_resolved).length

  // Group by category
  const grouped = todos.reduce(
    (acc, todo) => {
      const category = todo.category
      if (!acc[category]) acc[category] = []
      acc[category].push(todo)
      return acc
    },
    {} as Record<TodoCategory, TodoItem[]>
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex justify-between items-center">
          <span className="flex items-center gap-2">
            <CheckSquare className="h-5 w-5" />
            TODO Items
          </span>
          <span className="text-sm font-normal text-muted-foreground">
            {unresolvedCount} of {todos.length} items remaining
            {resolvedCount > 0 && (
              <span className="ml-2 text-green-600">({resolvedCount} resolved)</span>
            )}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {todos.length === 0 ? (
          <div className="text-center py-8">
            <CheckSquare className="h-12 w-12 mx-auto mb-4 text-green-500" />
            <p className="text-lg font-medium text-green-600">
              No manual work items identified
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              This report is ready for conversion.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {Object.entries(grouped).map(([category, categoryTodos]) => (
              <div key={category} className="space-y-3">
                <h4 className="font-medium flex items-center gap-2">
                  <span>{categoryLabels[category as TodoCategory] || category}</span>
                  <Badge variant="secondary" className="text-xs">
                    {categoryTodos.length}
                  </Badge>
                </h4>
                <div className="space-y-2">
                  {categoryTodos.map((todo) => (
                    <TodoItemCard
                      key={todo.id}
                      todo={todo}
                      onResolve={(resolved) => handleResolve(todo.id, resolved)}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
