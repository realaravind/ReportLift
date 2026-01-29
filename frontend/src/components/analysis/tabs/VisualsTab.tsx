/**
 * Visuals tab content for analysis features
 */

import { LayoutGrid, AlertCircle, MapPin } from 'lucide-react'
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
import type { VisualFeature, VisualType } from '@/types/analysis'

interface VisualsTabProps {
  visuals: VisualFeature[]
}

const unsupportedTypes: VisualType[] = ['map', 'gauge', 'subreport']

function VisualTypeBadge({ type }: { type: VisualType }) {
  const isUnsupported = unsupportedTypes.includes(type)

  const labels: Record<VisualType, string> = {
    tablix: 'Tablix',
    table: 'Table',
    matrix: 'Matrix',
    chart: 'Chart',
    gauge: 'Gauge',
    map: 'Map',
    subreport: 'Subreport',
    textbox: 'Textbox',
    image: 'Image',
    rectangle: 'Rectangle',
    line: 'Line',
    list: 'List',
  }

  return (
    <Badge variant={isUnsupported ? 'warning' : 'default'}>
      {labels[type] || type}
    </Badge>
  )
}

function getGroupingComplexity(
  rowGroups: number,
  columnGroups: number,
  hasRecursive: boolean
): string {
  const total = rowGroups + columnGroups
  if (hasRecursive) return 'Complex (Recursive)'
  if (total === 0) return 'None'
  if (total <= 2) return 'Simple'
  if (total <= 4) return 'Moderate'
  return 'Complex'
}

export function VisualsTab({ visuals }: VisualsTabProps) {
  if (visuals.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center text-muted-foreground">
        <LayoutGrid className="h-12 w-12 mb-4 opacity-50" />
        <p>No visual elements found in this report</p>
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
            <TableHead>Groups</TableHead>
            <TableHead>Complexity</TableHead>
            <TableHead>Flags</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {visuals.map((visual, index) => (
            <Collapsible key={index} asChild>
              <>
                <TableRow>
                  <TableCell>
                    <CollapsibleTrigger className="flex items-center gap-2 font-medium hover:underline cursor-pointer">
                      {visual.name}
                    </CollapsibleTrigger>
                  </TableCell>
                  <TableCell>
                    <VisualTypeBadge type={visual.type} />
                  </TableCell>
                  <TableCell>
                    {visual.row_groups > 0 || visual.column_groups > 0 ? (
                      <span>
                        {visual.row_groups}R / {visual.column_groups}C
                      </span>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {getGroupingComplexity(
                      visual.row_groups,
                      visual.column_groups,
                      visual.has_recursive_group
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      {unsupportedTypes.includes(visual.type) && (
                        <div className="flex items-center gap-1 text-yellow-600">
                          <AlertCircle className="h-4 w-4" />
                          <span className="text-xs">Unsupported</span>
                        </div>
                      )}
                      {visual.type === 'subreport' && (
                        <div className="flex items-center gap-1 text-blue-600">
                          <MapPin className="h-4 w-4" />
                          <span className="text-xs">External</span>
                        </div>
                      )}
                      {visual.has_recursive_group && (
                        <Badge variant="danger" className="text-xs">
                          Recursive
                        </Badge>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
                <CollapsibleContent asChild>
                  <TableRow className="bg-muted/50">
                    <TableCell colSpan={5} className="p-4">
                      <div className="space-y-4">
                        {visual.dataset_name && (
                          <div>
                            <span className="font-medium">Dataset: </span>
                            {visual.dataset_name}
                          </div>
                        )}
                        {visual.subreport_path && (
                          <div>
                            <span className="font-medium">Subreport Path: </span>
                            <code className="bg-muted px-2 py-1 rounded">
                              {visual.subreport_path}
                            </code>
                          </div>
                        )}
                        {visual.row_group_details.length > 0 && (
                          <div>
                            <span className="font-medium">Row Groups:</span>
                            <ul className="mt-1 space-y-1 pl-4">
                              {visual.row_group_details.map((group, idx) => (
                                <li key={idx} className="text-sm">
                                  {group.name}
                                  {group.is_recursive && (
                                    <Badge variant="danger" className="ml-2 text-xs">
                                      Recursive
                                    </Badge>
                                  )}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {visual.column_group_details.length > 0 && (
                          <div>
                            <span className="font-medium">Column Groups:</span>
                            <ul className="mt-1 space-y-1 pl-4">
                              {visual.column_group_details.map((group, idx) => (
                                <li key={idx} className="text-sm">
                                  {group.name}
                                  {group.is_recursive && (
                                    <Badge variant="danger" className="ml-2 text-xs">
                                      Recursive
                                    </Badge>
                                  )}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {visual.nested_item_count > 0 && (
                          <div>
                            <span className="font-medium">Nested Items: </span>
                            {visual.nested_item_count}
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
