/**
 * MaskedInput - Input component for sensitive values
 *
 * Displays masked value (dots) and reveals actual value on focus.
 * Includes show/hide toggle button.
 */

import { useState, forwardRef } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export interface MaskedInputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  /** Whether the value should be hidden by default */
  masked?: boolean
  /** Whether the field has an existing value (shows placeholder dots) */
  hasExistingValue?: boolean
  /** Placeholder when field has existing value */
  existingValuePlaceholder?: string
}

export const MaskedInput = forwardRef<HTMLInputElement, MaskedInputProps>(
  (
    {
      className,
      masked = true,
      hasExistingValue = false,
      existingValuePlaceholder = '••••••••',
      value,
      placeholder,
      onChange,
      ...props
    },
    ref
  ) => {
    const [isVisible, setIsVisible] = useState(!masked)
    const [isFocused, setIsFocused] = useState(false)

    // Show existing value placeholder if no value entered and has existing value
    const showExistingPlaceholder = hasExistingValue && !value && !isFocused

    return (
      <div className="relative">
        <Input
          ref={ref}
          type={isVisible ? 'text' : 'password'}
          className={cn('pr-10', className)}
          value={value}
          placeholder={showExistingPlaceholder ? existingValuePlaceholder : placeholder}
          onChange={onChange}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          {...props}
        />
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
          onClick={() => setIsVisible(!isVisible)}
          tabIndex={-1}
        >
          {isVisible ? (
            <EyeOff className="h-4 w-4 text-muted-foreground" />
          ) : (
            <Eye className="h-4 w-4 text-muted-foreground" />
          )}
          <span className="sr-only">{isVisible ? 'Hide' : 'Show'} password</span>
        </Button>
      </div>
    )
  }
)

MaskedInput.displayName = 'MaskedInput'

export default MaskedInput
