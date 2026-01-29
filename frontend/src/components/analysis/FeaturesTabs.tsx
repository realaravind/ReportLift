/**
 * Features tabs component for analysis display
 */

import { Database, LayoutGrid, Code, LayoutTemplate } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { DatasetsTab } from './tabs/DatasetsTab'
import { VisualsTab } from './tabs/VisualsTab'
import { ExpressionsTab } from './tabs/ExpressionsTab'
import { LayoutTab } from './tabs/LayoutTab'
import type { AnalysisFeatures } from '@/types/analysis'

interface FeaturesTabsProps {
  features: AnalysisFeatures | null
}

export function FeaturesTabs({ features }: FeaturesTabsProps) {
  if (!features) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Report Features</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            No feature data available
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Report Features</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="datasets" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="datasets" className="flex items-center gap-2">
              <Database className="h-4 w-4" />
              <span className="hidden sm:inline">Datasets</span>
              <span className="text-xs text-muted-foreground">
                ({features.datasets?.length || 0})
              </span>
            </TabsTrigger>
            <TabsTrigger value="visuals" className="flex items-center gap-2">
              <LayoutGrid className="h-4 w-4" />
              <span className="hidden sm:inline">Visuals</span>
              <span className="text-xs text-muted-foreground">
                ({features.visuals?.length || 0})
              </span>
            </TabsTrigger>
            <TabsTrigger value="expressions" className="flex items-center gap-2">
              <Code className="h-4 w-4" />
              <span className="hidden sm:inline">Expressions</span>
              <span className="text-xs text-muted-foreground">
                ({features.expressions?.length || 0})
              </span>
            </TabsTrigger>
            <TabsTrigger value="layout" className="flex items-center gap-2">
              <LayoutTemplate className="h-4 w-4" />
              <span className="hidden sm:inline">Layout</span>
            </TabsTrigger>
          </TabsList>

          <div className="mt-4">
            <TabsContent value="datasets">
              <DatasetsTab datasets={features.datasets || []} />
            </TabsContent>

            <TabsContent value="visuals">
              <VisualsTab visuals={features.visuals || []} />
            </TabsContent>

            <TabsContent value="expressions">
              <ExpressionsTab expressions={features.expressions || []} />
            </TabsContent>

            <TabsContent value="layout">
              <LayoutTab layout={features.layout} />
            </TabsContent>
          </div>
        </Tabs>
      </CardContent>
    </Card>
  )
}
