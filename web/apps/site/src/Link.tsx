import type { AnchorHTMLAttributes } from 'react'
import { navigate } from './router'

/** A link to a page of this site: it changes the page without a reload; a new-tab click works as usual. */
export function Link({ href, onClick, children, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) {
  return (
    <a
      href={href}
      onClick={(event) => {
        onClick?.(event)
        if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey) return
        event.preventDefault()
        navigate(href)
      }}
      {...rest}
    >
      {children}
    </a>
  )
}
