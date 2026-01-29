import { useState } from 'react'
import { AlertTriangle, Check, X, ChevronDown, ChevronUp, Code } from 'lucide-react'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'

export interface UncertainConversion {
  rewriteId: string
  spName: string
  spDefinition: string
  generatedSql?: string
  confidenceLevel: 'high' | 'medium' | 'low'
  confidenceScore: number
  aiExplanation?: string
  verificationStatus: 'pending' | 'verified' | 'rejected'
  reviewRecommendations: string[]
}

interface UncertainConversionCardProps {
  conversion: UncertainConversion
  onVerify: (rewriteId: string, notes?: string) => Promise<void>
  onReject: (rewriteId: string, notes?: string) => Promise<void>
  isLoading?: boolean
}

const confidenceColors = {
  high: 'bg-green-100 text-green-800 border-green-300',
  medium: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  low: 'bg-red-100 text-red-800 border-red-300',
}

const confidenceLabels = {
  high: 'High Confidence',
  medium: 'Medium Confidence',
  low: 'Low Confidence',
}

const statusColors = {
  pending: 'bg-yellow-100 text-yellow-800',
  verified: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
}

const statusLabels = {
  pending: 'Pending Review',
  verified: 'Verified',
  rejected: 'Rejected',
}

export function UncertainConversionCard({
  conversion,
  onVerify,
  onReject,
  isLoading = false,
}: UncertainConversionCardProps) {
  const [showOriginalSp, setShowOriginalSp] = useState(false)
  const [showGeneratedSql, setShowGeneratedSql] = useState(false)
  const [showVerifyDialog, setShowVerifyDialog] = useState(false)
  const [showRejectDialog, setShowRejectDialog] = useState(false)
  const [notes, setNotes] = useState('')

  const handleVerify = async () => {
    await onVerify(conversion.rewriteId, notes || undefined)
    setShowVerifyDialog(false)
    setNotes('')
  }

  const handleReject = async () => {
    await onReject(conversion.rewriteId, notes || undefined)
    setShowRejectDialog(false)
    setNotes('')
  }

  const isPending = conversion.verificationStatus === 'pending'

  return (
    <>
      <Card className={`border-2 ${isPending ? 'border-yellow-300 bg-yellow-50/30' : 'border-gray-200'}`}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {isPending && <AlertTriangle className="h-5 w-5 text-yellow-600" />}
              <CardTitle className="text-lg">{conversion.spName}</CardTitle>
            </div>
            <div className="flex items-center gap-2">
              <Badge className={confidenceColors[conversion.confidenceLevel]}>
                {confidenceLabels[conversion.confidenceLevel]}
              </Badge>
              <Badge className={statusColors[conversion.verificationStatus]}>
                {statusLabels[conversion.verificationStatus]}
              </Badge>
            </div>
          </div>
          <CardDescription>
            Confidence Score: {Math.round(conversion.confidenceScore * 100)}%
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* AI Explanation */}
          {conversion.aiExplanation && (
            <div className="rounded-md bg-muted p-3">
              <p className="text-sm font-medium mb-1">AI Explanation:</p>
              <p className="text-sm text-muted-foreground">{conversion.aiExplanation}</p>
            </div>
          )}

          {/* Review Recommendations */}
          {conversion.reviewRecommendations.length > 0 && (
            <div className="rounded-md border p-3">
              <p className="text-sm font-medium mb-2">Review Recommendations:</p>
              <ul className="list-disc list-inside space-y-1">
                {conversion.reviewRecommendations.map((rec, index) => (
                  <li key={index} className="text-sm text-muted-foreground">
                    {rec}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Original SP - Collapsible */}
          <Collapsible open={showOriginalSp} onOpenChange={setShowOriginalSp}>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" className="w-full justify-between p-0 h-auto">
                <span className="flex items-center gap-2 text-sm font-medium">
                  <Code className="h-4 w-4" />
                  Original Stored Procedure
                </span>
                {showOriginalSp ? (
                  <ChevronUp className="h-4 w-4" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )}
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-2">
              <div className="rounded-md bg-gray-900 p-3 overflow-x-auto">
                <pre className="text-sm text-gray-100 whitespace-pre-wrap">
                  {conversion.spDefinition}
                </pre>
              </div>
            </CollapsibleContent>
          </Collapsible>

          {/* Generated SQL - Collapsible */}
          {conversion.generatedSql && (
            <Collapsible open={showGeneratedSql} onOpenChange={setShowGeneratedSql}>
              <CollapsibleTrigger asChild>
                <Button variant="ghost" className="w-full justify-between p-0 h-auto">
                  <span className="flex items-center gap-2 text-sm font-medium">
                    <Code className="h-4 w-4" />
                    AI-Generated SQL
                  </span>
                  {showGeneratedSql ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2">
                <div className="rounded-md bg-gray-900 p-3 overflow-x-auto">
                  <pre className="text-sm text-gray-100 whitespace-pre-wrap">
                    {conversion.generatedSql}
                  </pre>
                </div>
              </CollapsibleContent>
            </Collapsible>
          )}
        </CardContent>

        {isPending && (
          <CardFooter className="flex justify-end gap-2 pt-3 border-t">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowRejectDialog(true)}
              disabled={isLoading}
            >
              <X className="h-4 w-4 mr-1" />
              Reject
            </Button>
            <Button
              variant="default"
              size="sm"
              onClick={() => setShowVerifyDialog(true)}
              disabled={isLoading}
              className="bg-green-600 hover:bg-green-700"
            >
              <Check className="h-4 w-4 mr-1" />
              Verify
            </Button>
          </CardFooter>
        )}
      </Card>

      {/* Verify Confirmation Dialog */}
      <AlertDialog open={showVerifyDialog} onOpenChange={setShowVerifyDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Verify Conversion</AlertDialogTitle>
            <AlertDialogDescription>
              You are accepting this AI-generated conversion for <strong>{conversion.spName}</strong>.
              The converted SQL will be included in the final output.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="py-4">
            <Label htmlFor="verify-notes">Notes (optional)</Label>
            <Textarea
              id="verify-notes"
              placeholder="Add any notes about your verification..."
              value={notes}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setNotes(e.target.value)}
              className="mt-2"
            />
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isLoading}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleVerify}
              disabled={isLoading}
              className="bg-green-600 hover:bg-green-700"
            >
              Confirm Verification
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Reject Confirmation Dialog */}
      <AlertDialog open={showRejectDialog} onOpenChange={setShowRejectDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Reject Conversion</AlertDialogTitle>
            <AlertDialogDescription>
              You are rejecting the AI-generated conversion for <strong>{conversion.spName}</strong>.
              A placeholder will be used instead, and the SP will remain in the TODO list for manual conversion.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="py-4">
            <Label htmlFor="reject-notes">Reason for rejection (optional)</Label>
            <Textarea
              id="reject-notes"
              placeholder="Explain why you're rejecting this conversion..."
              value={notes}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setNotes(e.target.value)}
              className="mt-2"
            />
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isLoading}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleReject}
              disabled={isLoading}
              className="bg-red-600 hover:bg-red-700"
            >
              Confirm Rejection
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}

export default UncertainConversionCard
