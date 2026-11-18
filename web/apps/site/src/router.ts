import { useSyncExternalStore } from 'react'

/** The site's pages. GitHub Pages serves every path from index.html (public/404.html), so each page has a real URL. */
export type Page = 'home' | 'features' | 'films' | 'install'

const BASE = import.meta.env.BASE_URL
const PATHS: Record<Page, string> = { home: '', features: 'features', films: 'films', install: 'install' }

export const href = (page: Page, hash = '') => BASE + PATHS[page] + hash

/** A file under public/, at the site's base path. */
export const asset = (path: string) => BASE + path

export function pageOf(pathname: string): Page {
  const rest = pathname.startsWith(BASE) ? pathname.slice(BASE.length) : pathname.replace(/^\//, '')
  const first = rest.split('/')[0] ?? ''
  return (Object.keys(PATHS) as Page[]).find((page) => PATHS[page] === first) ?? 'home'
}

function subscribe(onChange: () => void) {
  window.addEventListener('popstate', onChange)
  return () => {
    window.removeEventListener('popstate', onChange)
  }
}

export function usePage(): Page {
  return pageOf(useSyncExternalStore(subscribe, () => window.location.pathname))
}

/** Go to a URL of this site without a reload; `usePage` and the scroll follow. */
export function navigate(url: string) {
  window.history.pushState(null, '', url)
  window.dispatchEvent(new PopStateEvent('popstate'))
}
