/**
 * Datasets tab content for analysis features
 */

import { Database, AlertCircle } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
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
import type { DatasetFeature } from '@/types/analysis'

interface DatasetsTabProps {
  datasets: DatasetFeature[]
}

function QueryTypeBadge({ queryType }: { queryType: string }) {
  const variants: Record<string, 'default' | 'warning' | 'secondary'> = {
    stored_procedure: 'warning',
    embedded_sql: 'default',
    shared_dataset: 'secondary',
  }

  const labels: Record<string, string> = {
    stored_procedure: 'Stored Procedure',
    embedded_sql: 'Embedded SQL',
    shared_dataset: 'Shared Dataset',
  }

  return (
    <Badge variant={variants[queryType] || 'default'}>
      {labels[queryType] || queryType}
    </Badge>
  )
}

export function DatasetsTab({ datasets }: DatasetsTabProps) {
  if (datasets.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center text-muted-foreground">
        <Database className="h-12 w-12 mb-4 opacity-50" />
        <p>No datasets found in this report</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Parameters</TableHead>
            <TableHead>Fields</TableHead>
            <TableHead>Flags</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {datasets.map((dataset, index) => (
            <Collapsible key={index} asChild>
              <>
                <TableRow>
                  <TableCell>
                    <CollapsibleTrigger className="flex items-center gap-2 font-medium hover:underline cursor-pointer">
                      {dataset.name}
                    </CollapsibleTrigger>
                  </TableCell>
                  <TableCell>
                    <QueryTypeBadge queryType={dataset.query_type} />
                  </TableCell>
                  <TableCell>{dataset.parameter_count}</TableCell>
                  <TableCell>{dataset.field_count}</TableCell>
                  <TableCell>
                    {dataset.query_type === 'stored_procedure' && (
                      <div className="flex items-center gap-1 text-yellow-600">
                        <AlertCircle className="h-4 w-4" />
                        <span className="text-xs">SP</span>
                      </div>
                    )}
                  </TableCell>
                </TableRow>
                <CollapsibleContent asChild>
                  <TableRow className="bg-muted/50">
                    <TableCell colSpan={5} className="p-4">
                      <div className="space-y-4">
                        {dataset.stored_procedure_name && (
                          <div>
                            <span className="font-medium">Stored Procedure: </span>
                            <code className="bg-muted px-2 py-1 rounded">
                              {dataset.stored_procedure_name}
                            </code>
                          </div>
                        )}
                        {dataset.data_source_name && (
                          <div>
                            <span className="font-medium">Data Source: </span>
                            {dataset.data_source_name}
                          </div>
                        )}
                        {dataset.parameters.length > 0 && (
                          <div>
                            <span className="font-medium">Parameters:</span>
                            <ul className="mt-1 space-y-1 pl-4">
                              {dataset.parameters.map((param, idx) => (
                                <li key={idx} className="text-sm">
                                  <code>{param.name}</code>
                                  {param.data_type && (
                                    <span className="text-muted-foreground">
                                      {' '}
                                      ({param.data_type})
                                    </span>
                                  )}
                                  {param.default_value && (
                                    <span className="text-muted-foreground">
                                      {' '}
                                      = {param.default_value}
                                    </span>
                                  )}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {dataset.command_text && (
                          <div>
                            <span className="font-medium">Query:</span>
                            <pre className="mt-1 p-2 bg-muted rounded text-xs overflow-x-auto max-h-48">
                              {dataset.command_text}
                            </pre>
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
