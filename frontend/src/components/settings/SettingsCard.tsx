/**
 * SettingsCard - Reusable wrapper component for settings sections
 *
 * Provides consistent styling and layout for settings content.
 */

import { ReactNode } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export interface SettingsCardProps {
  title: string
  description?: string
  children: ReactNode
  actions?: ReactNode
}

export function SettingsCard({
  title,
  description,
  children,
  actions,
}: SettingsCardProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle>{title}</CardTitle>
            {description && (
              <CardDescription className="mt-1">{description}</CardDescription>
            )}
          </div>
          {actions && <div className="flex gap-2">{actions}</div>}
        </div>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}

export default SettingsCard
