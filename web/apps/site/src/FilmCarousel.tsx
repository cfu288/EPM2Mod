import { type CSSProperties, useEffect, useRef, useState } from 'react'
import { ChevronDownIcon, ChevronLeftIcon, ChevronRightIcon, ChevronUpIcon } from '@heroicons/react/20/solid'
import { HeartIcon } from '@heroicons/react/24/solid'
import { HeartIcon as HeartOutlineIcon } from '@heroicons/react/24/outline'
import { filmById } from '@epm2mod/ui'
import photos from './filmPhotos.json'
import { asset } from './router'
import './like.css'

/** A RAW file developed in the camera with each look; made by web/scripts/film_photos.py. */
interface Scene {
  id: string
  looks: Record<string, string>
  thumb: string
  width: number
  height: number
}

const scenes = photos as Scene[]
const NATURAL = 'natural'

const lookName = (id: string) => (id === NATURAL ? 'Natural' : filmById(id).name)
const lookFilm = (id: string) => (id === NATURAL ? 'Natural' : filmById(id).film)
const looksOf = (scene: number) => Object.keys(scenes[scene]?.looks ?? {})
const wrap = (i: number, n: number) => (i + n) % n

/** The liked film simulations live only in this browser. */
const LIKES = 'epm2mod-liked-films'
const readLikes = (): string[] => {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(LIKES) ?? '[]')
    return Array.isArray(value) ? value.filter((id): id is string => typeof id === 'string') : []
  } catch {
    return []
  }
}
const saveLikes = (ids: string[]) => {
  try {
    localStorage.setItem(LIKES, JSON.stringify(ids))
  } catch {
    // private mode or blocked storage: the likes last until the page closes
  }
}

/** A key as a keycap: a thicker bottom edge. */
const Key = ({ children }: { children: string }) => (
  <kbd className="border-ink-soft text-ink inline-flex h-6 min-w-6 items-center justify-center rounded-xs border border-b-[3px] bg-white px-1 font-sans text-xs">
    {children}
  </kbd>
)

/** Photos on two axes: left and right change the look, up and down change the scene. */
export function FilmCarousel() {
  const [scene, setScene] = useState(0)
  const [look, setLook] = useState('portra-400')
  const [liked, setLiked] = useState(readLikes)
  const [popped, setPopped] = useState<string | null>(null) // the film simulation just liked, while it animates
  const swipe = useRef<{ x: number; y: number } | null>(null)
  const root = useRef<HTMLDivElement>(null)
  const keys = useRef<Record<string, () => void>>({})
  const looks = looksOf(scene)
  const current = scenes[scene]

  const toggleLike = (id: string) => {
    const next = liked.includes(id) ? liked.filter((x) => x !== id) : [...liked, id]
    setLiked(next)
    saveLikes(next)
    setPopped(next.includes(id) ? id : null)
  }

  const moveLook = (step: number) => {
    setLook(looks[wrap(looks.indexOf(look) + step, looks.length)] ?? NATURAL)
  }
  const goScene = (next: number) => {
    const n = wrap(next, scenes.length)
    setScene(n)
    if (!looksOf(n).includes(look)) setLook(NATURAL)
  }

  // the neighbours on both axes load ahead, so a step shows at once
  useEffect(() => {
    const next = [
      looks[wrap(looks.indexOf(look) + 1, looks.length)],
      looks[wrap(looks.indexOf(look) - 1, looks.length)],
    ].map((id) => id && current?.looks[id])
    for (const s of [scene + 1, scene - 1]) next.push(scenes[wrap(s, scenes.length)]?.looks[look])
    for (const src of next) if (src) new Image().src = asset(src)
  }, [scene, look, looks, current])

  useEffect(() => {
    keys.current = {
      ArrowLeft: () => {
        moveLook(-1)
      },
      ArrowRight: () => {
        moveLook(1)
      },
      ArrowUp: () => {
        goScene(scene - 1)
      },
      ArrowDown: () => {
        goScene(scene + 1)
      },
    }
  })

  // The arrow keys work while focus is in the carousel, or while the pointer is over it and nothing has focus.
  useEffect(() => {
    const el = root.current
    if (!el) return
    let over = false
    const enter = () => {
      over = true
    }
    const leave = () => {
      over = false
    }
    const key = (event: KeyboardEvent) => {
      const active = document.activeElement
      if (!el.contains(active) && !(over && (!active || active === document.body))) return
      const step = keys.current[event.key]
      if (!step) return
      event.preventDefault()
      step()
    }
    el.addEventListener('pointerenter', enter)
    el.addEventListener('pointerleave', leave)
    document.addEventListener('keydown', key)
    return () => {
      el.removeEventListener('pointerenter', enter)
      el.removeEventListener('pointerleave', leave)
      document.removeEventListener('keydown', key)
    }
  }, [])

  if (!current) return null
  const src = current.looks[look] ?? current.looks[NATURAL] ?? ''

  return (
    <div
      role="region"
      aria-label="Film simulation comparison"
      aria-roledescription="carousel"
      ref={root}
      className="grid gap-4 lg:grid-cols-[1fr_7rem]"
    >
      <div className="min-w-0">
        <div
          className="relative flex h-[62vh] min-h-72 touch-pan-y items-center justify-center bg-neutral-100 select-none"
          onPointerDown={(event) => {
            swipe.current = { x: event.clientX, y: event.clientY }
          }}
          onPointerUp={(event) => {
            const start = swipe.current
            swipe.current = null
            if (!start) return
            const dx = event.clientX - start.x
            if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(event.clientY - start.y)) moveLook(dx < 0 ? 1 : -1)
          }}
        >
          <img
            src={asset(src)}
            alt={`Scene ${String(scene + 1)} in ${lookName(look)}`}
            width={current.width}
            height={current.height}
            draggable={false}
            className="max-h-full w-auto max-w-full object-contain"
          />
          <button
            type="button"
            aria-label="Previous film simulation"
            onClick={() => {
              moveLook(-1)
            }}
            className="absolute top-1/2 left-0 -translate-y-1/2 bg-white/80 p-2 hover:bg-white"
          >
            <ChevronLeftIcon aria-hidden="true" className="size-6" />
          </button>
          <button
            type="button"
            aria-label="Next film simulation"
            onClick={() => {
              moveLook(1)
            }}
            className="absolute top-1/2 right-0 -translate-y-1/2 bg-white/80 p-2 hover:bg-white"
          >
            <ChevronRightIcon aria-hidden="true" className="size-6" />
          </button>
          {look !== NATURAL && (
            <button
              type="button"
              aria-pressed={liked.includes(look)}
              aria-label={`Like ${lookName(look)}`}
              onClick={() => {
                toggleLike(look)
              }}
              className="focus-visible:outline-ink absolute right-3 bottom-3 rounded-full bg-white/90 p-3 shadow-md hover:bg-white focus-visible:outline-2 focus-visible:outline-offset-2"
            >
              {liked.includes(look) ? (
                <HeartIcon aria-hidden="true" className={`like-heart size-6 ${popped === look ? 'like-pop' : ''}`} />
              ) : (
                <HeartOutlineIcon aria-hidden="true" className="size-6" />
              )}
              {popped === look &&
                [-40, 0, 40].map((angle) => (
                  <span
                    key={angle}
                    aria-hidden="true"
                    className="like-burst"
                    style={{ '--angle': `${String(angle)}deg` } as CSSProperties}
                    onAnimationEnd={() => {
                      setPopped(null)
                    }}
                  />
                ))}
            </button>
          )}
        </div>

        <div className="mt-4 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1" aria-live="polite">
          <p>
            <span className="font-display text-2xl font-extrabold">{lookFilm(look)}</span>
          </p>
          <p className="text-muted hidden items-center gap-1 text-sm sm:flex">
            <Key>←</Key>
            <Key>→</Key>
            <span className="mr-3 ml-1">film simulation</span>
            <Key>↑</Key>
            <Key>↓</Key>
            <span className="ml-1">scene</span>
          </p>
        </div>

        <div role="group" aria-label="Film simulation" className="mt-4 flex flex-wrap gap-1">
          {looks.map((id) => (
            <button
              key={id}
              type="button"
              aria-pressed={id === look}
              onClick={() => {
                setLook(id)
              }}
              className="btn aria-pressed:bg-ink shrink-0 aria-pressed:text-white"
            >
              {lookName(id)}
              {liked.includes(id) && (
                <>
                  <HeartIcon aria-hidden="true" className="like-heart size-4" />
                  <span className="sr-only">, liked</span>
                </>
              )}
            </button>
          ))}
        </div>
      </div>

      <div className="flex min-w-0 items-center gap-2 lg:flex-col">
        <button
          type="button"
          aria-label="Previous scene"
          onClick={() => {
            goScene(scene - 1)
          }}
          className="btn hidden p-1 lg:inline-flex"
        >
          <ChevronUpIcon aria-hidden="true" className="size-5" />
        </button>
        <div
          role="group"
          aria-label="Scene"
          className="flex gap-2 overflow-x-auto lg:max-h-[62vh] lg:flex-col lg:overflow-y-auto"
        >
          {scenes.map((s, i) => (
            <button
              key={s.id}
              type="button"
              aria-pressed={i === scene}
              aria-label={`Scene ${String(i + 1)}`}
              onClick={() => {
                goScene(i)
              }}
              className="aria-pressed:border-ink shrink-0 border-2 border-transparent opacity-60 transition-opacity hover:opacity-100 aria-pressed:opacity-100"
            >
              <img src={asset(s.thumb)} alt="" className="size-16 object-cover lg:size-24" loading="lazy" />
            </button>
          ))}
        </div>
        <button
          type="button"
          aria-label="Next scene"
          onClick={() => {
            goScene(scene + 1)
          }}
          className="btn hidden p-1 lg:inline-flex"
        >
          <ChevronDownIcon aria-hidden="true" className="size-5" />
        </button>
      </div>
    </div>
  )
}
