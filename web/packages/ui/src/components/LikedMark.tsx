import { HeartIcon } from '@heroicons/react/16/solid'

/** The heart after the name of a film simulation the reader liked on the site. */
export function LikedMark() {
  return (
    <>
      <HeartIcon aria-hidden="true" className="text-like ml-1.5 inline size-4 align-[-3px]" />
      <span className="sr-only">, liked</span>
    </>
  )
}
