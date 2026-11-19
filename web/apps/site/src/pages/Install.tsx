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
    </Step>
  )
}

function CustomMenu({ n }: { n: number }) {
  return (
    <Step n={n} title="Show the Custom Menu">
      <p>
        Most features are in the Custom Menu (gears tab). If it is missing: MENU → Setup Menu (wrench) → Menu Display →
        Custom Menu → On.
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
        <p>MENU → Custom Menu → J → Load Looks → Load. Until then, the ART entries are the Olympus art filters.</p>
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
      <Step n={2} title="Make the firmware">
        <p>Format the SD card in the camera first. Then, with the card in the computer:</p>
        <Code>{'uv run epm2mod make --card /path/to/card'}</Code>
        <p>
          <code>/path/to/card</code> is the card&apos;s folder: <code>uv run epm2mod cards</code> lists it.
        </p>
        <p>
          <code>make</code> also writes the 12 default film simulations. To choose your own, put a command-line name
          from the{' '}
          <Link href={href('films', '#all-films')} className="underline">
            film simulation list
          </Link>{' '}
          in each ART slot. ART1 is the first entry of the camera&apos;s ART menu (Pop Art), ART12 the last
          (Watercolor). A slot you leave out keeps its Olympus art filter.
        </p>
        <Code>{'uv run epm2mod looks pack ART1=portra-400 ART2=velvia --card /path/to/card'}</Code>
      </Step>
      <Flash n={3} />
      <CustomMenu n={4} />
      <Step n={5} title="Load the film simulations">
        <p>MENU → Custom Menu → J → Load Looks → Load. Until then, the ART entries are the Olympus art filters.</p>
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

      <section className="min-w-0">
        <h2 className="section-title border-t-[6px] pt-4 text-lg">If something does not work</h2>
        <ul className="text-ink-soft mt-3 max-w-2xl list-disc space-y-2 pl-5">
          <li>
            The camera starts normally instead of writing: it found no firmware file it accepts. Make the card again.
          </li>
          <li>
            Load Looks shows No file: <code>EPM2LOOK.BIN</code> is not in the top folder of the card.
          </li>
          <li>Load Looks shows Bad file: the file is damaged or incomplete. Make it again. Nothing was changed.</li>
        </ul>
      </section>
    </div>
  )
}
