/**
 * Settings Page - Tabbed interface for application configuration
 *
 * Provides configuration management for SSRS, Snowflake, Ollama, and System settings.
 * Tab state is persisted in URL query parameters for browser navigation support.
 */

import { useSearchParams, useNavigate } from 'react-router-dom'
import { Settings as SettingsIcon, FileText } from 'lucide-react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { SSRSSettings } from '@/components/settings/SSRSSettings'
import { SnowflakeSettings } from '@/components/settings/SnowflakeSettings'
import { OllamaSettings } from '@/components/settings/OllamaSettings'
import { SystemSettings } from '@/components/settings/SystemSettings'
import { TemplateUpload } from '@/components/settings/TemplateUpload'

const VALID_TABS = ['ssrs', 'snowflake', 'ollama', 'branding', 'system'] as const
type TabValue = (typeof VALID_TABS)[number]

const DEFAULT_TAB: TabValue = 'ssrs'

export function Settings() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()

  // Get current tab from URL, defaulting to SSRS
  const currentTab = (searchParams.get('tab') as TabValue) || DEFAULT_TAB
  const validTab = VALID_TABS.includes(currentTab) ? currentTab : DEFAULT_TAB

  // Update URL when tab changes
  const handleTabChange = (value: string) => {
    setSearchParams({ tab: value }, { replace: true })
  }

  return (
    <div className="container mx-auto max-w-4xl py-6 px-4">
      {/* Page Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <SettingsIcon className="h-6 w-6" />
            <h1 className="text-2xl font-bold">Settings</h1>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/audit')}
            className="gap-2"
          >
            <FileText className="h-4 w-4" />
            Audit Logs
          </Button>
        </div>
        <p className="text-muted-foreground">
          Configure connections and application settings.
        </p>
      </div>

      {/* Tabbed Interface */}
      <Tabs value={validTab} onValueChange={handleTabChange} className="space-y-4">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="ssrs">SSRS</TabsTrigger>
          <TabsTrigger value="snowflake">Snowflake</TabsTrigger>
          <TabsTrigger value="ollama">Ollama</TabsTrigger>
          <TabsTrigger value="branding">Branding</TabsTrigger>
          <TabsTrigger value="system">System</TabsTrigger>
        </TabsList>

        <TabsContent value="ssrs" className="space-y-4">
          <SSRSSettings />
        </TabsContent>

        <TabsContent value="snowflake" className="space-y-4">
          <SnowflakeSettings />
        </TabsContent>

        <TabsContent value="ollama" className="space-y-4">
          <OllamaSettings />
        </TabsContent>

        <TabsContent value="branding" className="space-y-4">
          <TemplateUpload />
        </TabsContent>

        <TabsContent value="system" className="space-y-4">
          <SystemSettings onNavigateToTab={handleTabChange} />
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default Settings
