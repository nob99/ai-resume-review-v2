'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { useAuth } from '@/contexts/AuthContext'
import { useToastActions } from '@/components/ui/Toast'
import { cn } from '@/lib/utils'
import Button from '@/components/ui/Button'
import Container from './Container'
import EnvironmentBadge from './EnvironmentBadge'

export interface HeaderProps {
  className?: string
  showUserMenu?: boolean
}

// User menu dropdown component
const UserMenu: React.FC<{ isOpen: boolean; onToggle: () => void }> = ({ isOpen, onToggle }) => {
  const { user, logout } = useAuth()
  const { showSuccess, showError } = useToastActions()

  const handleLogout = async () => {
    try {
      await logout()
      showSuccess('Successfully logged out')
    } catch {
      showError('Failed to log out')
    }
    onToggle() // Close menu
  }

  if (!user) return null

  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="sm"
        onClick={onToggle}
        className="flex items-center gap-2 px-3 py-2"
        aria-haspopup="true"
        aria-expanded={isOpen}
      >
        {/* User avatar */}
        <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-medium">
          {user.first_name?.[0]?.toUpperCase() || user.email[0].toUpperCase()}
        </div>
        <span className="hidden sm:inline-block font-medium text-neutral-700">
          {user.first_name || user.email}
        </span>
        {/* Chevron down icon */}
        <svg
          className={cn(
            'w-4 h-4 text-neutral-500 transition-transform duration-200',
            isOpen && 'rotate-180'
          )}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </Button>

      {/* Dropdown menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-48 bg-white border border-neutral-200 rounded-md shadow-lg z-50">
          <div className="py-1">
            {/* User info */}
            <div className="px-4 py-2 border-b border-neutral-100">
              <p className="text-sm font-medium text-neutral-900">
                {user.first_name} {user.last_name}
              </p>
              <p className="text-sm text-neutral-500 truncate">
                {user.email}
              </p>
              {user.role && (
                <span className="inline-block mt-1 px-2 py-0.5 text-xs bg-primary-100 text-primary-700 rounded">
                  {user.role}
                </span>
              )}
            </div>

            {/* Menu items */}
            <a
              href="/profile"
              className="block w-full text-left px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-50 focus:bg-neutral-50"
              onClick={onToggle}
            >
              Profile Settings
            </a>

            <hr className="my-1 border-neutral-100" />

            <button
              onClick={handleLogout}
              className="block w-full text-left px-4 py-2 text-sm text-error-600 hover:bg-error-50 focus:bg-error-50"
            >
              Sign Out
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// Main navigation items
const NavigationItems: React.FC = () => {
  const { user } = useAuth()

  return (
    <nav className="hidden md:flex items-center space-x-8">
      <a
        href="/upload"
        className="text-neutral-700 hover:text-primary-600 px-3 py-2 text-sm font-medium transition-colors"
      >
        Upload Resume
      </a>
      <a
        href="/history"
        className="text-neutral-700 hover:text-primary-600 px-3 py-2 text-sm font-medium transition-colors"
      >
        Review History
      </a>
      <a
        href="/register-candidate"
        className="text-neutral-700 hover:text-primary-600 px-3 py-2 text-sm font-medium transition-colors"
      >
        Register Candidate
      </a>
      {user?.role === 'admin' && (
        <a
          href="/admin"
          className="text-neutral-700 hover:text-primary-600 px-3 py-2 text-sm font-medium transition-colors"
        >
          User Management
        </a>
      )}
    </nav>
  )
}

// Mobile menu component
const MobileMenu: React.FC<{ isOpen: boolean; onToggle: () => void }> = ({ isOpen, onToggle }) => {
  const { user } = useAuth()
  return (
    <>
      {/* Mobile menu button */}
      <button
        type="button"
        onClick={onToggle}
        className="md:hidden inline-flex items-center justify-center p-2 rounded-md text-neutral-700 hover:text-primary-600 hover:bg-neutral-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
        aria-controls="mobile-menu"
        aria-expanded={isOpen}
      >
        <span className="sr-only">Open main menu</span>
        {isOpen ? (
          // Close icon
          <svg
            className="w-6 h-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          // Hamburger icon
          <svg
            className="w-6 h-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        )}
      </button>

      {/* Mobile menu panel */}
      {isOpen && (
        <div className="md:hidden absolute top-full left-0 right-0 bg-white border-b border-neutral-200 shadow-lg" id="mobile-menu">
          <div className="px-2 pt-2 pb-3 space-y-1">
            <a
              href="/upload"
              className="block px-3 py-2 text-base font-medium text-neutral-700 hover:text-primary-600 hover:bg-neutral-50 rounded-md"
              onClick={onToggle}
            >
              Upload Resume
            </a>
            <a
              href="/history"
              className="block px-3 py-2 text-base font-medium text-neutral-700 hover:text-primary-600 hover:bg-neutral-50 rounded-md"
              onClick={onToggle}
            >
              Review History
            </a>
            <a
              href="/register-candidate"
              className="block px-3 py-2 text-base font-medium text-neutral-700 hover:text-primary-600 hover:bg-neutral-50 rounded-md"
              onClick={onToggle}
            >
              Register Candidate
            </a>
            {user?.role === 'admin' && (
              <a
                href="/admin"
                className="block px-3 py-2 text-base font-medium text-neutral-700 hover:text-primary-600 hover:bg-neutral-50 rounded-md"
                onClick={onToggle}
              >
                User Management
              </a>
            )}
          </div>
        </div>
      )}
    </>
  )
}

// Main Header component
const Header: React.FC<HeaderProps> = ({ className, showUserMenu = true }) => {
  const { isAuthenticated } = useAuth()
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const toggleUserMenu = () => {
    setUserMenuOpen(!userMenuOpen)
    setMobileMenuOpen(false) // Close mobile menu when user menu opens
  }

  const toggleMobileMenu = () => {
    setMobileMenuOpen(!mobileMenuOpen)
    setUserMenuOpen(false) // Close user menu when mobile menu opens
  }

  // Close menus when clicking outside
  React.useEffect(() => {
    const handleClickOutside = () => {
      setUserMenuOpen(false)
      setMobileMenuOpen(false)
    }

    if (userMenuOpen || mobileMenuOpen) {
      document.addEventListener('click', handleClickOutside)
      return () => document.removeEventListener('click', handleClickOutside)
    }
  }, [userMenuOpen, mobileMenuOpen])

  return (
    <header className={cn('bg-white border-b border-neutral-200 relative', className)}>
      <Container size="full">
        <div className="flex items-center justify-between h-16">
          {/* Logo and brand */}
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center">
              {/* Brand text */}
              <div className="flex flex-col">
                <span className="font-bold text-xl text-neutral-900 leading-tight">
                  Yatagarasu
                </span>
                <span className="text-[12px] text-neutral-500">
                  Resume Review
                </span>
              </div>
            </Link>
            <EnvironmentBadge />
          </div>

          {/* Navigation and user menu */}
          {isAuthenticated && (
            <div className="flex items-center space-x-4">
              <NavigationItems />
              
              <div className="flex items-center space-x-2">
                {showUserMenu && (
                  <div onClick={(e) => e.stopPropagation()}>
                    <UserMenu isOpen={userMenuOpen} onToggle={toggleUserMenu} />
                  </div>
                )}
                
                <div onClick={(e) => e.stopPropagation()}>
                  <MobileMenu isOpen={mobileMenuOpen} onToggle={toggleMobileMenu} />
                </div>
              </div>
            </div>
          )}
        </div>
      </Container>
    </header>
  )
}

export default Header