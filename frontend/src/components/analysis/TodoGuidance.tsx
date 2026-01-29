/**
 * AI-Generated Todo Guidance Component
 *
 * Displays structured guidance for TODO items with:
 * - Summary section (always visible)
 * - Expandable detailed explanation
 * - Numbered action steps
 * - Challenges and references
 * - DAX equivalent (for expressions)
 * - Copy to clipboard functionality
 */

import { useState } from 'react'
import {
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  Sparkles,
  FileText,
  AlertTriangle,
  ExternalLink,
  Loader2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { cn } from '@/lib/utils'

export interface TodoGuidanceData {
  summary: string
  detailed_explanation: string
  suggested_steps: string[]
  challenges?: string[] | null
  references?: string[] | null
  dax_equivalent?: string | null
  power_bi_config?: string | null
  generated_by: 'ai' | 'template'
  generated_at: string
  cached?: boolean
}

interface TodoGuidanceProps {
  guidance: TodoGuidanceData
  todoTitle?: string
  itemName?: string
  category?: string
  isLoading?: boolean
  onRefresh?: () => void
}

export function TodoGuidance({
  guidance,
  todoTitle,
  itemName,
  category: _category,
  isLoading = false,
  onRefresh,
}: TodoGuidanceProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    const text = formatGuidanceForClipboard(guidance, todoTitle, itemName)
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const isAiGenerated = guidance.generated_by === 'ai'

  return (
    <div className="space-y-3">
      {/* Summary - always visible */}
      <div className="p-3 bg-blue-50 dark:bg-blue-950 rounded-lg border border-blue-200 dark:border-blue-800">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm text-blue-900 dark:text-blue-100">{guidance.summary}</p>
          <Badge
            variant="outline"
            className={cn(
              'flex-shrink-0 text-xs',
              isAiGenerated
                ? 'bg-purple-50 border-purple-200 text-purple-700'
                : 'bg-gray-50 border-gray-200 text-gray-600'
            )}
          >
            {isAiGenerated ? (
              <>
                <Sparkles className="h-3 w-3 mr-1" />
                AI
              </>
            ) : (
              <>
                <FileText className="h-3 w-3 mr-1" />
                Template
              </>
            )}
          </Badge>
        </div>
      </div>

      {/* Expandable details */}
      <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
        <CollapsibleTrigger asChild>
          <Button variant="ghost" size="sm" className="w-full justify-between">
            <span className="text-sm">
              {isExpanded ? 'Hide Details' : 'Show Details'}
            </span>
            {isExpanded ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent className="space-y-4 pt-2">
          {/* Detailed explanation */}
          {guidance.detailed_explanation && (
            <div className="space-y-1">
              <h5 className="text-sm font-medium text-muted-foreground">Details</h5>
              <p className="text-sm">{guidance.detailed_explanation}</p>
            </div>
          )}

          {/* Suggested steps */}
          {guidance.suggested_steps && guidance.suggested_steps.length > 0 && (
            <div className="space-y-2">
              <h5 className="text-sm font-medium text-muted-foreground">
                Suggested Steps
              </h5>
              <ol className="list-decimal list-inside space-y-1.5 text-sm">
                {guidance.suggested_steps.map((step, index) => (
                  <li key={index} className="pl-1">
                    {step}
                  </li>
                ))}
              </ol>
            </div>
          )}

          {/* DAX equivalent */}
          {guidance.dax_equivalent && (
            <div className="space-y-1">
              <h5 className="text-sm font-medium text-muted-foreground">
                DAX Equivalent
              </h5>
              <pre className="text-xs font-mono bg-muted p-3 rounded overflow-x-auto">
                {guidance.dax_equivalent}
              </pre>
            </div>
          )}

          {/* Power BI configuration */}
          {guidance.power_bi_config && (
            <div className="space-y-1">
              <h5 className="text-sm font-medium text-muted-foreground">
                Power BI Configuration
              </h5>
              <p className="text-sm bg-muted p-2 rounded">{guidance.power_bi_config}</p>
            </div>
          )}

          {/* Challenges */}
          {guidance.challenges && guidance.challenges.length > 0 && (
            <div className="space-y-2">
              <h5 className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                <AlertTriangle className="h-3.5 w-3.5 text-yellow-600" />
                Challenges to Watch For
              </h5>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                {guidance.challenges.map((challenge, index) => (
                  <li key={index}>{challenge}</li>
                ))}
              </ul>
            </div>
          )}

          {/* References */}
          {guidance.references && guidance.references.length > 0 && (
            <div className="space-y-2">
              <h5 className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                <ExternalLink className="h-3.5 w-3.5" />
                References
              </h5>
              <ul className="list-disc list-inside space-y-1 text-sm">
                {guidance.references.map((ref, index) => {
                  // Check if it's a URL
                  const urlMatch = ref.match(/https?:\/\/[^\s]+/)
                  if (urlMatch) {
                    return (
                      <li key={index}>
                        <a
                          href={urlMatch[0]}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline"
                        >
                          {ref.replace(urlMatch[0], '').trim() || urlMatch[0]}
                        </a>
                      </li>
                    )
                  }
                  return <li key={index}>{ref}</li>
                })}
              </ul>
            </div>
          )}
        </CollapsibleContent>
      </Collapsible>

      {/* Actions */}
      <div className="flex items-center justify-between pt-1">
        <Button
          variant="outline"
          size="sm"
          onClick={handleCopy}
          disabled={isLoading}
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5 mr-1.5 text-green-600" />
              Copied
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5 mr-1.5" />
              Copy Guidance
            </>
          )}
        </Button>

        <div className="flex items-center gap-2">
          {onRefresh && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onRefresh}
              disabled={isLoading}
            >
              {isLoading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Sparkles className="h-3.5 w-3.5" />
              )}
              <span className="ml-1.5">
                {isLoading ? 'Generating...' : 'Regenerate'}
              </span>
            </Button>
          )}
          {guidance.cached && (
            <span className="text-xs text-muted-foreground">(cached)</span>
          )}
        </div>
      </div>
    </div>
  )
}

/**
 * Format guidance for clipboard copy
 */
function formatGuidanceForClipboard(
  guidance: TodoGuidanceData,
  todoTitle?: string,
  itemName?: string
): string {
  let text = ''

  if (todoTitle) {
    text += `## ${todoTitle}\n\n`
  }
  if (itemName) {
    text += `**Item:** ${itemName}\n\n`
  }

  text += `**Summary:** ${guidance.summary}\n\n`

  if (guidance.detailed_explanation) {
    text += `### Details\n${guidance.detailed_explanation}\n\n`
  }

  if (guidance.suggested_steps && guidance.suggested_steps.length > 0) {
    text += `### Suggested Steps\n`
    guidance.suggested_steps.forEach((step, i) => {
      text += `${i + 1}. ${step}\n`
    })
    text += '\n'
  }

  if (guidance.dax_equivalent) {
    text += `### DAX Equivalent\n\`\`\`dax\n${guidance.dax_equivalent}\n\`\`\`\n\n`
  }

  if (guidance.power_bi_config) {
    text += `### Power BI Configuration\n${guidance.power_bi_config}\n\n`
  }

  if (guidance.challenges && guidance.challenges.length > 0) {
    text += `### Challenges to Watch For\n`
    guidance.challenges.forEach((c) => {
      text += `- ${c}\n`
    })
    text += '\n'
  }

  if (guidance.references && guidance.references.length > 0) {
    text += `### References\n`
    guidance.references.forEach((ref) => {
      text += `- ${ref}\n`
    })
  }

  text += `\n---\n*Generated: ${guidance.generated_by === 'ai' ? 'AI-assisted' : 'Template'}*`

  return text
}

export default TodoGuidance
