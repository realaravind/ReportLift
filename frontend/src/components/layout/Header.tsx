/**
 * Header Component - Fixed header with logo, settings, and user actions
 */

import { useNavigate, useLocation } from 'react-router-dom'
import { Menu, Settings, User, LogOut } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { useUIStore } from '@/store/uiStore'
import { useAuthStore } from '@/store/authStore'
import { useHealthStore } from '@/store/healthStore'
import { cn } from '@/lib/utils'

export function Header() {
  const navigate = useNavigate()
  const location = useLocation()
  const { toggleMobileDrawer } = useUIStore()
  const { user, logout } = useAuthStore()
  const { disconnectedCount } = useHealthStore()

  const isSettingsActive = location.pathname === '/settings'
  const hasWarning = disconnectedCount > 0

  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-16 border-b border-border bg-background">
      <div className="flex h-full items-center justify-between px-4">
        {/* Left section - Logo and mobile menu */}
        <div className="flex items-center gap-4">
          {/* Mobile menu button - visible only on small screens */}
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={toggleMobileDrawer}
            aria-label="Toggle navigation menu"
          >
            <Menu className="h-5 w-5" />
          </Button>

          {/* Logo/Title */}
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground font-bold">
              R
            </div>
            <span className="text-xl font-semibold">ReportLift</span>
          </div>
        </div>

        {/* Right section - Settings and User */}
        <div className="flex items-center gap-2">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Settings"
                  onClick={() => navigate('/settings')}
                  className={cn('relative', isSettingsActive && 'bg-accent')}
                >
                  <Settings className="h-5 w-5" />
                  {hasWarning && (
                    <span className="absolute top-1 right-1 flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-orange-400 opacity-75" />
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-orange-500" />
                    </span>
                  )}
                </Button>
              </TooltipTrigger>
              {hasWarning && (
                <TooltipContent side="bottom">
                  <p>
                    {disconnectedCount === 1
                      ? '1 connection needs attention'
                      : `${disconnectedCount} connections need attention`}
                  </p>
                </TooltipContent>
              )}
            </Tooltip>
          </TooltipProvider>

          {/* User menu with dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="User menu">
                <User className="h-5 w-5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              {user && (
                <>
                  <DropdownMenuLabel>
                    <div className="flex flex-col space-y-1">
                      <p className="text-sm font-medium leading-none">{user.username}</p>
                      <p className="text-xs leading-none text-muted-foreground">
                        {user.identity}
                      </p>
                    </div>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                </>
              )}
              <DropdownMenuItem onClick={logout}>
                <LogOut className="mr-2 h-4 w-4" />
                <span>Log out</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  )
}
