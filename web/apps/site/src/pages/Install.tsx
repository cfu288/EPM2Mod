import { useState, type KeyboardEvent, type ReactNode } from 'react'
import { ArrowDownTrayIcon } from '@heroicons/react/20/solid'
import { REPO } from '@epm2mod/ui'
import { Link } from '../Link'
import { href } from '../router'

// No release yet: /releases/latest would send people to an empty list. Point it there once one exists.
const DOWNLOAD = `${REPO}/releases`
const UV = 'https://docs.astral.sh/uv/getting-started/installation/'

type Way = 'installer' | 'cli'
const WAYS: { id: Way; label: string }[] = [
  { id: 'installer', label: 'Installer' },
  { id: 'cli', label: 'Command line' },
]

function Step({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return (
    <li className="border-rule grid gap-4 border-t py-8 sm:grid-cols-[4rem_1fr]">
      <span className="font-display text-muted text-3xl font-extrabold">{n}</span>
      <div className="min-w-0">
        <h2 className="text-xl font-bold">{title}</h2>
        <div className="text-ink-soft mt-3 space-y-2">{children}</div>
      </div>
    </li>
  )
}

function Code({ children }: { children: string }) {
  return <pre className="bg-neutral-100 p-3 text-sm break-all whitespace-pre-wrap">{children}</pre>
}

function Flash({ n }: { n: number }) {
  return (
    <Step n={n} title="Flash">
      <p>Charge the battery fully. With the camera off, put the card in.</p>
      <p>
        Press and hold OK (the centre of the arrow pad) and ON/OFF together. Let go when the orange lamp on the front
        stays lit.
      </p>
      <p>Writing takes 1 to 2 minutes. Do not switch the camera off until the lamp blinks.</p>
      <p>When the lamp blinks, switch the camera off and on again.</p>
      <p>Check that MENU → SETUP → wrench tab → Firmware reads Body : 1.6 EPM2Mod and the release date.</p>
    </Step>
  )
}

function CustomMenu({ n }: { n: number }) {
  return (
    <Step n={n} title="Show the Custom Menu">
      <p>
        Most features are in the Custom Menu (gears tab). If it is missing: MENU → SETUP → Setup Menu (wrench tab) →
        Menu Display → Custom Menu → On.
      </p>
    </Step>
  )
}

function InstallerSteps() {
  return (
    <ol>
      <Step n={1} title="Download">
        <p>Get the EPM2Mod zip and unzip it.</p>
        <a href={DOWNLOAD} className="btn bg-ink hover:text-ink mt-2 py-3 text-white hover:bg-white">
          Download from GitHub
          <ArrowDownTrayIcon aria-hidden="true" className="size-5" />
        </a>
      </Step>
      <Step n={2} title="Start">
        <dl className="grid grid-cols-[6rem_1fr] gap-y-2">
          <dt className="font-bold">Mac</dt>
          <dd>
            Double-click <code>Start (Mac).command</code>. The first time, macOS blocks it: open System Settings →
            Privacy &amp; Security, scroll down, select Open Anyway next to it, then Open.
          </dd>
          <dt className="font-bold">Windows</dt>
          <dd>
            Double-click <code>Start (Windows).bat</code>. If Windows warns you: More info → Run anyway.
          </dd>
          <dt className="font-bold">Linux</dt>
          <dd>
            Run <code>./start.sh</code>.
          </dd>
        </dl>
      </Step>
      <Step n={3} title="Make the firmware">
        <p>
          Format the SD card in the camera first. A page opens in your browser: follow it to write the firmware to the
          card.
        </p>
      </Step>
      <Flash n={4} />
      <CustomMenu n={5} />
      <Step n={6} title="Load the film simulations">
        <p>
          MENU → SETUP → Custom Menu → J → Load Looks → Load. Until then, the ART entries are the Olympus art filters.
        </p>
      </Step>
    </ol>
  )
}

function CliSteps() {
  return (
    <ol>
      <Step n={1} title="Get the code">
        <p>
          Install{' '}
          <a href={UV} className="underline">
            uv
          </a>
          , then:
        </p>
        <Code>{`git clone ${REPO}.git\ncd EPM2Mod`}</Code>
      </Step>
      <Step n={2} title="Write the card">
        <p>Format the SD card in the camera first. Then, with the card in the computer:</p>
        <Code>
          {
            'uv run epm2mod install --card /path/to/card --film ART1=portra-400 --film ART2=ektachrome --film ART3=pro-400h --film ART4=kodachrome --film ART5=double-x --film ART6=vision3-250d --film ART7=velvia --film ART8=superia-400 --film ART9=provia --film ART10=portra-160 --film ART11=gold-200 --film ART12=vision3-500t'
          }
        </Code>
        <p>
          <code>/path/to/card</code> is the card&apos;s folder: <code>uv run epm2mod cards</code> lists it. To use other
          film simulations, change the names (
          <Link href={href('films', '#all-films')} className="underline">
            film simulation list
          </Link>
          ).
        </p>
      </Step>
      <Flash n={3} />
      <CustomMenu n={4} />
      <Step n={5} title="Load the film simulations">
        <p>
          MENU → SETUP → Custom Menu → J → Load Looks → Load. Until then, the ART entries are the Olympus art filters.
        </p>
      </Step>
    </ol>
  )
}

export function Install() {
  const [way, setWay] = useState<Way>(() => (window.location.hash === '#command-line' ? 'cli' : 'installer'))
  const choose = (next: Way) => {
    setWay(next)
    window.history.replaceState(null, '', next === 'cli' ? '#command-line' : window.location.pathname)
  }
  const onKey = (event: KeyboardEvent) => {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return
    const next = way === 'installer' ? 'cli' : 'installer'
    choose(next)
    document.getElementById(`tab-${next}`)?.focus()
  }

  return (
    <div className="mx-auto grid max-w-4xl gap-12 px-4 py-12 sm:px-6 lg:px-8 lg:py-16">
      <div className="min-w-0">
        <h1 className="font-display text-4xl font-extrabold tracking-tight sm:text-5xl">Install</h1>

        <div role="tablist" aria-label="How to install" className="mt-8 flex gap-1">
          {WAYS.map((w) => (
            <button
              key={w.id}
              id={`tab-${w.id}`}
              type="button"
              role="tab"
              aria-selected={way === w.id}
              aria-controls="install-steps"
              tabIndex={way === w.id ? 0 : -1}
              onKeyDown={onKey}
              onClick={() => {
                choose(w.id)
              }}
              className="btn aria-selected:bg-ink aria-selected:text-white"
            >
              {w.label}
            </button>
          ))}
        </div>

        <div id="install-steps" role="tabpanel" aria-labelledby={`tab-${way}`} className="mt-6">
          {way === 'installer' ? <InstallerSteps /> : <CliSteps />}
        </div>
      </div>

      <section className="min-w-0">
        <h2 className="section-title border-t-[6px] pt-4 text-lg">Change the film simulations</h2>
        {way === 'installer' ? (
          <p className="text-ink-soft mt-3">
            Start the installer again and pick Film simulations only. Then load them with Load Looks, without a flash.
          </p>
        ) : (
          <div className="text-ink-soft mt-3 max-w-2xl space-y-2">
            <Code>{'uv run epm2mod films set --card /path/to/card --film ART2=velvia'}</Code>
            <p>Then load them with Load Looks, without a flash.</p>
          </div>
        )}
      </section>

      <section className="min-w-0">
        <h2 className="section-title border-t-[6px] pt-4 text-lg">Remove EPM2Mod</h2>
        {way === 'installer' ? (
          <p className="text-ink-soft mt-3">
            Start the installer again and pick Olympus original as the firmware. Flash it the same way.
          </p>
        ) : (
          <div className="text-ink-soft mt-3 max-w-2xl space-y-2">
            <Code>{'uv run epm2mod restore --card /path/to/card'}</Code>
            <p>Then flash it the same way.</p>
          </div>
        )}
      </section>
    </div>
  )
}
