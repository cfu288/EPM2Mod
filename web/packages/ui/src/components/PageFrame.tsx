import type { ReactNode } from 'react'

export const REPO = 'https://github.com/cfu288/EPM2Mod'

/** The header and the page's own content; `footer` goes under a rule at the bottom. */
export function PageFrame({
  subtitle,
  children,
  footer,
}: {
  subtitle: string
  children: ReactNode
  footer?: ReactNode
}) {
  return (
    <div className="min-h-full">
      <header className="border-rule border-b bg-white">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-x-4 px-4 sm:px-6 lg:px-8">
          <a href={REPO} className="font-display text-xl font-extrabold tracking-tight">
            EPM2Mod
          </a>
          <span className="text-muted text-sm font-light tracking-wider">{subtitle}</span>
        </div>
      </header>
      {children}
      {footer && (
        <footer className="border-rule border-t">
          <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">{footer}</div>
        </footer>
      )}
    </div>
  )
}
