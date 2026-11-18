import type { ReactNode } from 'react'
import { ArrowUpRightIcon } from '@heroicons/react/20/solid'
import { FilmCredit, REPO } from '@epm2mod/ui'
import { Link } from './Link'
import { href, type Page } from './router'

const NAV: { page: Page; label: string }[] = [
  { page: 'features', label: 'Features' },
  { page: 'films', label: 'Films' },
  { page: 'install', label: 'Install' },
]

export function Layout({ page, children }: { page: Page; children: ReactNode }) {
  return (
    <div className="flex min-h-full flex-col">
      <header className="border-rule sticky top-0 z-20 border-b bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-x-4 px-4 sm:px-6 lg:px-8">
          <Link href={href('home')} className="font-display text-lg font-extrabold tracking-tight sm:text-xl">
            EPM2Mod
          </Link>
          <nav aria-label="Main">
            <ul className="flex items-center gap-x-4 text-sm sm:gap-x-8">
              {NAV.map((item) => (
                <li key={item.page}>
                  <Link
                    href={href(item.page)}
                    aria-current={page === item.page ? 'page' : undefined}
                    className="hover:border-ink aria-[current=page]:border-ink border-b-2 border-transparent py-1 aria-[current=page]:font-bold"
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
              <li>
                <a
                  href={REPO}
                  className="hover:border-ink inline-flex items-center gap-x-0.5 border-b-2 border-transparent py-1"
                >
                  GitHub
                  <ArrowUpRightIcon aria-hidden="true" className="size-3.5" />
                </a>
              </li>
            </ul>
          </nav>
        </div>
      </header>

      <main className="flex-1">{children}</main>

      <footer className="border-ink border-t-[6px]">
        <div className="text-muted mx-auto flex max-w-7xl flex-col gap-y-2 px-4 py-8 text-xs sm:px-6 lg:px-8">
          <p>Unofficial. Not made or supported by OM Digital Solutions. Use at your own risk.</p>
          <FilmCredit />
        </div>
      </footer>
    </div>
  )
}
