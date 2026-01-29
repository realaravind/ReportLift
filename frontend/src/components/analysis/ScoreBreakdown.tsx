/**
 * Score breakdown visualization component
 */

import { TrendingDown } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import type { ScoreBreakdown as ScoreBreakdownType, ConversionStatus } from '@/types/analysis'

interface ScoreBreakdownProps {
  breakdown: ScoreBreakdownType | null
  status: ConversionStatus | null
  score: number | null
}

const progressColors: Record<ConversionStatus, string> = {
  green: '[&>div]:bg-green-500',
  yellow: '[&>div]:bg-yellow-500',
  red: '[&>div]:bg-red-500',
}

const scoreColors: Record<ConversionStatus, string> = {
  green: 'text-green-600',
  yellow: 'text-yellow-600',
  red: 'text-red-600',
}

export function ScoreBreakdown({ breakdown, status, score }: ScoreBreakdownProps) {
  const effectiveStatus = status || 'yellow'
  const finalScore = score ?? breakdown?.final_score ?? 0
  const penalties = breakdown?.penalties ?? []

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingDown className="h-5 w-5" />
          Score Breakdown
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Progress bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span>Conversion Score</span>
            <span className={`font-medium ${scoreColors[effectiveStatus]}`}>
              {finalScore}%
            </span>
          </div>
          <Progress
            value={finalScore}
            className={`h-3 ${progressColors[effectiveStatus]}`}
          />
        </div>

        {/* Penalty breakdown */}
        <div className="space-y-2 pt-2 border-t">
          <div className="flex justify-between text-sm font-medium">
            <span>Base Score</span>
            <span>100%</span>
          </div>

          {penalties.length > 0 ? (
            <>
              {penalties.map((penalty, index) => (
                <div
                  key={index}
                  className="flex justify-between text-sm pl-4 text-muted-foreground"
                >
                  <span className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-red-400 rounded-full" />
                    <span className="truncate max-w-[300px]" title={penalty.reason}>
                      {penalty.item_name
                        ? `${penalty.category}: ${penalty.item_name}`
                        : penalty.reason}
                    </span>
                  </span>
                  <span className="text-red-600 flex-shrink-0">
                    -{penalty.penalty_percent}%
                  </span>
                </div>
              ))}
            </>
          ) : (
            <div className="text-sm text-muted-foreground pl-4">
              No penalties applied
            </div>
          )}

          <div className="flex justify-between text-sm font-medium border-t pt-2">
            <span>Final Score</span>
            <span className={scoreColors[effectiveStatus]}>{finalScore}%</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
