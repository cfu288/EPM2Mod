import type { ReactNode } from 'react'

export const REPO = 'https://github.com/cfu288/EPM2Mod'

/** The header, the page's own content and the footer with the credit for the film fits. */
export function PageFrame({ subtitle, children }: { subtitle: string; children: ReactNode }) {
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
      <footer className="border-rule border-t">
        <p className="text-muted mx-auto max-w-7xl px-4 py-6 text-xs sm:px-6 lg:px-8">
          The film looks are fitted from{' '}
          <a className="hover:text-ink underline" href="https://github.com/andreavolpato/spektrafilm">
            spektrafilm
          </a>{' '}
          by Andrea Volpato (CC BY-SA 4.0).
        </p>
      </footer>
    </div>
  )
}
