import { useState } from 'react'
import { AlertTriangle, ChevronDown, ChevronUp, CheckCircle, XCircle, Clock } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { UncertainConversionCard, type UncertainConversion } from './UncertainConversionCard'

export interface UncertainConversionsSummary {
  totalAiRewrites: number
  uncertainCount: number
  highConfidenceCount: number
  mediumConfidenceCount: number
  lowConfidenceCount: number
  pendingReviewCount: number
  verifiedCount: number
  rejectedCount: number
}

interface UncertainConversionsSectionProps {
  summary: UncertainConversionsSummary
  conversions: UncertainConversion[]
  onVerify: (rewriteId: string, notes?: string) => Promise<void>
  onReject: (rewriteId: string, notes?: string) => Promise<void>
  isLoading?: boolean
}

export function UncertainConversionsSection({
  summary,
  conversions,
  onVerify,
  onReject,
  isLoading = false,
}: UncertainConversionsSectionProps) {
  const [isOpen, setIsOpen] = useState(true)

  const reviewProgress = summary.uncertainCount > 0
    ? ((summary.verifiedCount + summary.rejectedCount) / summary.uncertainCount) * 100
    : 100

  const hasPendingReviews = summary.pendingReviewCount > 0
  const pendingConversions = conversions.filter(c => c.verificationStatus === 'pending')
  const reviewedConversions = conversions.filter(c => c.verificationStatus !== 'pending')

  if (summary.uncertainCount === 0) {
    return (
      <Alert className="bg-green-50 border-green-200">
        <CheckCircle className="h-4 w-4 text-green-600" />
        <AlertTitle className="text-green-800">All Conversions Confident</AlertTitle>
        <AlertDescription className="text-green-700">
          All AI conversions have high confidence and do not require manual review.
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-4">
      {/* Summary Alert */}
      <Alert className={hasPendingReviews ? 'bg-yellow-50 border-yellow-200' : 'bg-blue-50 border-blue-200'}>
        <AlertTriangle className={`h-4 w-4 ${hasPendingReviews ? 'text-yellow-600' : 'text-blue-600'}`} />
        <AlertTitle className={hasPendingReviews ? 'text-yellow-800' : 'text-blue-800'}>
          {hasPendingReviews
            ? `${summary.pendingReviewCount} conversion${summary.pendingReviewCount > 1 ? 's' : ''} need review`
            : 'All uncertain conversions reviewed'}
        </AlertTitle>
        <AlertDescription className={hasPendingReviews ? 'text-yellow-700' : 'text-blue-700'}>
          {summary.uncertainCount} uncertain conversion{summary.uncertainCount > 1 ? 's' : ''} detected
          ({summary.mediumConfidenceCount} medium, {summary.lowConfidenceCount} low confidence)
        </AlertDescription>
      </Alert>

      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Review Progress</span>
          <span className="font-medium">
            {summary.verifiedCount + summary.rejectedCount} of {summary.uncertainCount} reviewed
          </span>
        </div>
        <Progress value={reviewProgress} className="h-2" />
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <CheckCircle className="h-3 w-3 text-green-600" />
              {summary.verifiedCount} verified
            </span>
            <span className="flex items-center gap-1">
              <XCircle className="h-3 w-3 text-red-600" />
              {summary.rejectedCount} rejected
            </span>
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3 text-yellow-600" />
              {summary.pendingReviewCount} pending
            </span>
          </div>
        </div>
      </div>

      {/* Collapsible Section */}
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger asChild>
          <Button variant="outline" className="w-full justify-between">
            <span className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-yellow-600" />
              Uncertain Conversions
              <Badge variant="secondary">{summary.uncertainCount}</Badge>
            </span>
            {isOpen ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent className="mt-4 space-y-4">
          {/* Pending Reviews Section */}
          {pendingConversions.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-sm font-medium flex items-center gap-2">
                <Clock className="h-4 w-4 text-yellow-600" />
                Pending Review ({pendingConversions.length})
              </h4>
              <div className="space-y-3">
                {pendingConversions.map((conversion) => (
                  <UncertainConversionCard
                    key={conversion.rewriteId}
                    conversion={conversion}
                    onVerify={onVerify}
                    onReject={onReject}
                    isLoading={isLoading}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Already Reviewed Section */}
          {reviewedConversions.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-sm font-medium flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-600" />
                Reviewed ({reviewedConversions.length})
              </h4>
              <div className="space-y-3">
                {reviewedConversions.map((conversion) => (
                  <UncertainConversionCard
                    key={conversion.rewriteId}
                    conversion={conversion}
                    onVerify={onVerify}
                    onReject={onReject}
                    isLoading={isLoading}
                  />
                ))}
              </div>
            </div>
          )}
        </CollapsibleContent>
      </Collapsible>
    </div>
  )
}

export default UncertainConversionsSection
