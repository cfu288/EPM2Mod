import { useEffect, useId, useState, type ReactNode } from 'react'
import { ArrowDownTrayIcon, ArrowPathIcon } from '@heroicons/react/20/solid'
import {
  builtInSlots,
  CARD_NAME,
  choicesOf,
  filmById,
  FilmCredit,
  MenuEditor,
  PageFrame,
  slots,
  StripPreview,
  useLooks,
  type Looks,
  type SlotItem,
} from '@epm2mod/ui'
import { api, type Build, type Card, type Firmware, type Job } from './api'
import { Timeline } from './Timeline'

type StepId = 'start' | 'firmware' | 'films' | 'build' | 'install'
const LABELS: Record<StepId, string> = {
  start: 'Start',
  firmware: 'Firmware',
  films: 'Film looks',
  build: 'Build',
  install: 'Install',
}
/** The steps of each choice of firmware: Olympus's own has no film looks. */
const FLOWS: Record<Firmware, StepId[]> = {
  epm2mod: ['start', 'firmware', 'films', 'build', 'install'],
  original: ['start', 'firmware', 'build', 'install'],
}
const ZIP_NAME = 'EPM2Mod-card.zip'

/** A sentence that names the first slot whose film differs from the default, for the check after Load Looks. */
function changedSlot(items: readonly SlotItem[]): string {
  const index = items.findIndex((item, i) => item.filmId !== null && item.filmId !== slots[i]?.builtIn)
  const id = items[index]?.filmId
  return id ? `ART ${String(index + 1)} shows ${filmById(id).name}.` : 'The list shows your films.'
}
const HELP = 'https://github.com/cfu288/EPM2Mod/blob/main/docs/install.md'

/** A card in the list: its name, size and where it is mounted. */
const cardLabel = (c: Card) => `${c.name || 'SD card'} · ${String(Math.round(c.size / 1e9))} GB · ${c.path}`
const DEFAULT_CHOICES = choicesOf(builtInSlots()).join()

/** What the user sees while the job runs, and the step of the job (`steps` of `epm2mod serve`) that ends each one. */
function stages(job: Job | null, firmware: Firmware) {
  const write = job?.card == null ? 'Prepare the zip' : 'Write to the SD card'
  if (firmware === 'original')
    return [
      { label: "Download Olympus's firmware and check it", step: 1 },
      { label: write, step: 2 },
    ]
  return [
    { label: "Download Olympus's firmware", step: 1 },
    { label: 'Add EPM2Mod', step: 3 },
    { label: 'Check the result', step: 4 },
    { label: write, step: 5 },
  ]
}

function save(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = name
  link.click()
  URL.revokeObjectURL(url)
}

const message = (error: unknown) => (error instanceof Error ? error.message : String(error))

const primary =
  'btn bg-ink hover:text-ink disabled:bg-rule justify-center px-6 py-3 text-base text-white hover:bg-white'
const secondary = 'btn justify-center px-6 py-3 text-base'

/** One step's page: its title, its content and its buttons. */
function Step({ title, children, actions }: { title: string; children?: ReactNode; actions?: ReactNode }) {
  return (
    <section aria-labelledby="step-title" className="space-y-6">
      <h1 id="step-title" className="font-display text-3xl font-extrabold tracking-tight">
        {title}
      </h1>
      {children}
      {actions && <div className="flex flex-col-reverse gap-3 sm:flex-row sm:flex-wrap sm:justify-end">{actions}</div>}
    </section>
  )
}

function BackButton({ onClick }: { onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className={`${secondary} sm:mr-auto`}>
      Back
    </button>
  )
}

/** One choice: a large radio with a title and one line under it, and more content when chosen. */
function Choice(props: {
  group: string
  title: string
  line: string
  checked: boolean
  onChoose: () => void
  children?: ReactNode
}) {
  const id = useId()
  return (
    <div className={`border p-4 ${props.checked ? 'border-ink' : 'border-rule'}`}>
      <div className="flex items-start gap-x-3">
        <input
          id={id}
          type="radio"
          name={props.group}
          aria-describedby={`${id}-line`}
          checked={props.checked}
          onChange={props.onChoose}
          className="accent-ink mt-1 size-4"
        />
        <div>
          <label htmlFor={id} className="block cursor-pointer font-bold">
            {props.title}
          </label>
          <p id={`${id}-line`} className="text-ink-soft text-sm">
            {props.line}
          </p>
        </div>
      </div>
      {props.checked && props.children}
    </div>
  )
}

function StartStep(props: {
  zip: boolean
  onZip: (zip: boolean) => void
  cards: Card[]
  card: string
  onCard: (card: string) => void
  onNext: () => void
  ready: boolean
}) {
  return (
    <Step
      title="Install firmware on your PEN E-PM2"
      actions={
        <button type="button" disabled={!props.ready} onClick={props.onNext} className={primary}>
          Next
        </button>
      }
    >
      <div className="space-y-3">
        <Choice
          group="output"
          title="Write to an SD card"
          line="Put the camera's SD card in this computer. Your photos stay on it."
          checked={!props.zip}
          onChoose={() => {
            props.onZip(false)
          }}
        >
          <div className="mt-4 space-y-2 pl-7 text-sm">
            {props.cards.length > 0 ? (
              <>
                <label htmlFor="card" className="block font-bold">
                  Card
                </label>
                <select
                  id="card"
                  value={props.card}
                  onChange={(event) => {
                    props.onCard(event.target.value)
                  }}
                  className="border-ink w-full border bg-white px-2 py-2"
                >
                  {props.cards.map((c) => (
                    <option key={c.path} value={c.path}>
                      {cardLabel(c)}
                    </option>
                  ))}
                </select>
                {props.cards.length > 1 && (
                  <p className="text-ink-soft">Not sure which? Take the camera&apos;s card out: its entry goes away.</p>
                )}
              </>
            ) : (
              <>
                <p className="flex items-center gap-x-2">
                  <ArrowPathIcon aria-hidden="true" className="size-4 animate-spin" />
                  Insert the camera&apos;s SD card. It shows here when found.
                </p>
                <p className="text-ink-soft">
                  No card slot? Connect the camera to this computer with its USB cable, turn the camera on, and choose
                  Storage on its screen.
                </p>
              </>
            )}
          </div>
        </Choice>
        <Choice
          group="output"
          title="Download a zip"
          line="Copy the files to the card yourself."
          checked={props.zip}
          onChoose={() => {
            props.onZip(true)
          }}
        />
      </div>
    </Step>
  )
}

function FirmwareStep(props: {
  firmware: Firmware
  onFirmware: (firmware: Firmware) => void
  onBack: () => void
  onNext: () => void
}) {
  return (
    <Step
      title="Choose the firmware"
      actions={
        <>
          <BackButton onClick={props.onBack} />
          <button type="button" onClick={props.onNext} className={primary}>
            Next
          </button>
        </>
      }
    >
      <div className="space-y-3">
        <Choice
          group="firmware"
          title="EPM2Mod"
          line="Unofficial, made by independent developers. Adds film looks, interval shooting, a level gauge and focus peaking. You can put the Olympus original back here at any time."
          checked={props.firmware === 'epm2mod'}
          onChoose={() => {
            props.onFirmware('epm2mod')
          }}
        />
        <Choice
          group="firmware"
          title="Olympus original"
          line="Olympus's own firmware. It removes EPM2Mod."
          checked={props.firmware === 'original'}
          onChoose={() => {
            props.onFirmware('original')
          }}
        />
      </div>
    </Step>
  )
}

function FilmsStep(props: {
  zip: boolean
  looks: Looks
  customizing: boolean
  onCustomize: (on: boolean) => void
  onBuild: (custom: boolean) => void
  onBack: () => void
}) {
  if (!props.customizing)
    return (
      <Step
        title="Film looks"
        actions={
          <>
            <BackButton onClick={props.onBack} />
            <button
              type="button"
              onClick={() => {
                props.onCustomize(true)
              }}
              className={secondary}
            >
              Customize
            </button>
            <button
              type="button"
              onClick={() => {
                props.onBuild(false)
              }}
              className={primary}
            >
              Use the default films
            </button>
          </>
        }
      >
        <p>
          EPM2Mod replaces the 12 art filters in the ART menu with film looks. Customize picks the films and their
          order.
        </p>
        <FilmCredit />
      </Step>
    )
  const { looks } = props
  return (
    <Step
      title="Customize the film looks"
      actions={
        <>
          <BackButton
            onClick={() => {
              props.onCustomize(false)
            }}
          />
          <button
            type="button"
            onClick={() => {
              if (window.confirm('Discard your changes and use the default films?')) looks.reset()
            }}
            className={secondary}
          >
            Reset to the default films
          </button>
          <button
            type="button"
            onClick={() => {
              props.onBuild(true)
            }}
            className={primary}
          >
            {props.zip ? 'Make the zip' : 'Write to the card'}
          </button>
        </>
      }
    >
      <div className="sticky top-0 z-10 -mx-4 bg-white px-4 py-2">
        <div className="max-w-md">
          <StripPreview art={looks.selected + 1} filmId={looks.items[looks.selected]?.filmId ?? null} />
        </div>
      </div>
      <MenuEditor looks={looks} />
      <FilmCredit />
    </Step>
  )
}

function BuildStep(props: { job: Job | null; firmware: Firmware; onRetry: () => void; onBack: () => void }) {
  const { job } = props
  const failed = job?.error != null
  const list = stages(job, props.firmware)
  const doneCount = list.filter(
    (stage) => job !== null && job.step >= stage.step && (stage.step < job.steps || (job.done && !failed)),
  ).length
  const title = props.firmware === 'original' ? 'Getting the original firmware' : 'Building'
  const failedTitle =
    doneCount === 0
      ? 'Could not download the firmware'
      : doneCount === list.length - 1
        ? job?.card == null
          ? 'Could not make the zip'
          : 'Could not write to the card'
        : 'The build stopped'
  return (
    <Step
      title={failed ? failedTitle : title}
      actions={
        failed && (
          <>
            <BackButton onClick={props.onBack} />
            <button type="button" onClick={props.onRetry} className={primary}>
              Try again
            </button>
          </>
        )
      }
    >
      <ol aria-label="Progress" aria-live="polite" className="space-y-2">
        {list.map((stage, index) => {
          const state = index < doneCount ? 'done' : index === doneCount ? (failed ? 'failed' : 'now') : 'later'
          const style = { done: '', now: 'font-bold', failed: 'font-bold', later: 'text-muted' }[state]
          return (
            <li key={stage.step} className={`flex items-center gap-x-2 ${style}`}>
              <span aria-hidden="true" className="inline-flex w-4 justify-center">
                {state === 'now' ? (
                  <ArrowPathIcon className="size-4 animate-spin" />
                ) : (
                  { done: '✓', failed: '✗', later: '·' }[state]
                )}
              </span>
              {stage.label}
            </li>
          )
        })}
      </ol>
      {failed ? (
        <p role="alert" className="border-ink border-l-4 pl-3 text-sm whitespace-pre-wrap">
          {job.error}
        </p>
      ) : (
        <p className="text-ink-soft text-sm">
          Takes about a minute and needs the internet.
          {job?.card != null && ' Keep the card in this computer until it finishes.'}
        </p>
      )}
    </Step>
  )
}

function InstallStep(props: {
  job: Job
  cardName: string
  /** A sentence that names a slot the user changed, for the check, for example "ART 2 shows C200." */
  changed: string
  onZip: () => void
  onRestart: () => void
}) {
  const { job } = props
  const zip = job.card === null
  const looks = job.files.includes(CARD_NAME)
  const original = job.firmware === 'original'
  const what = original ? "Olympus's original firmware" : 'EPM2Mod'
  return (
    <Step
      title="Install on the camera"
      actions={
        <button type="button" onClick={props.onRestart} className={secondary}>
          Start over
        </button>
      }
    >
      <p className="font-bold">
        {zip ? 'Done. Your zip is ready.' : `Done. ${what} is on the card ${props.cardName}.`}
      </p>
      {zip && (
        <button type="button" onClick={props.onZip} className={`${primary} w-full`}>
          <ArrowDownTrayIcon aria-hidden="true" className="size-5" />
          Download {ZIP_NAME}
        </button>
      )}
      <ol aria-label="Install steps" className="list-decimal space-y-2 pl-5">
        {zip && (
          <li>
            Open {ZIP_NAME}. Copy the DCOLYMP folder{looks ? ` and the file ${CARD_NAME}` : ''} from it to the top level
            of the SD card.
          </li>
        )}
        <li>
          Eject the SD card and take it out (or unplug the camera&apos;s USB cable). Mac: in Finder, select ⏏ next to
          the card. Windows: in File Explorer, right-click the card and select Eject.
        </li>
        <li>
          Charge the camera&apos;s battery fully. With the camera off, open the battery/card cover on the bottom, put
          the battery in, and push the card in until it clicks. Close the cover.
        </li>
        <li>Press and hold the OK button (the middle of the arrow pad). While you hold it, press the ON/OFF button.</li>
        <li>
          When an orange lamp lights, let go of OK. The lamp stays on for 1 to 2 minutes while the camera updates. Until
          it blinks, keep the cover closed, the battery in, and the buttons untouched. Still on after 10 minutes? Get
          help (link below).
        </li>
        <li>
          When the lamp blinks, the update is done. Press ON/OFF to turn the camera off, then again to turn it on.
        </li>
        {looks ? (
          <>
            <li>
              Press MENU and select SETUP (use the arrow pad to move and OK to select): a menu with tabs on the left
              opens. If it has no gears tab: open the wrench tab → Menu Display → set Custom Menu (the gears) to On.
            </li>
            <li>Open the gears tab → group J → Load Looks → Load → OK. The row shows Loaded.</li>
            <li>To check: press MENU and select ART. {props.changed}</li>
          </>
        ) : (
          <li>
            {original
              ? 'To check: press MENU and select ART. The list shows the art filters, such as Pop Art.'
              : 'To check: press MENU and select ART. The list shows film names, such as Portra 400.'}
          </li>
        )}
      </ol>
      <p className="text-ink-soft text-sm">
        The camera starts as usual instead? Turn it off and repeat step {zip ? 4 : 3}. Something else?{' '}
        <a className="hover:text-ink underline" href={HELP}>
          Get help
        </a>
        .
      </p>
      <p className="text-ink-soft text-sm">When the camera is updated, close this page and the EPM2Mod text window.</p>
    </Step>
  )
}

export default function App() {
  const looks = useLooks()
  const [step, setStep] = useState<StepId>('start')
  const [firmware, setFirmware] = useState<Firmware>('epm2mod')
  const [customizing, setCustomizing] = useState(false)
  const [build, setBuild] = useState<Build | null>(null)
  const [cards, setCards] = useState<Card[]>([])
  const [zip, setZip] = useState(false)
  const [card, setCard] = useState('')
  const [job, setJob] = useState<Job | null>(null)
  const [problem, setProblem] = useState<string | null>(null)
  const [lastCustom, setLastCustom] = useState(false)
  const running = job !== null && !job.done
  const flow = FLOWS[firmware]

  const refreshCards = () => {
    api.cards().then(
      (found) => {
        setCards(found)
        setCard((current) => (found.some((c) => c.path === current) ? current : (found[0]?.path ?? '')))
      },
      (error: unknown) => {
        setProblem(message(error))
      },
    )
  }

  useEffect(() => {
    api.build().then(setBuild, (error: unknown) => {
      setProblem(message(error))
    })
    refreshCards()
  }, [])

  // on the first screen, look for cards every 2 seconds
  const searching = step === 'start' && !zip
  useEffect(() => {
    if (!searching) return
    const timer = window.setInterval(refreshCards, 2000)
    return () => {
      window.clearInterval(timer)
    }
  }, [searching])

  useEffect(() => {
    if (!running) return
    const timer = window.setInterval(() => {
      api.job().then(
        (next) => {
          setJob(next)
          if (next?.done && next.error === null) setStep('install')
        },
        (error: unknown) => {
          setProblem(message(error))
        },
      )
    }, 500)
    return () => {
      window.clearInterval(timer)
    }
  }, [running])

  const startBuild = (custom: boolean) => {
    setProblem(null)
    setLastCustom(custom)
    const choices = choicesOf(looks.items)
    // films left as they are need no look file: the firmware has them built in
    const wanted = firmware === 'epm2mod' && custom && choices.join() !== DEFAULT_CHOICES ? choices : []
    setJob(null)
    setStep('build')
    api.make(firmware, wanted, zip ? null : card).then(
      (started) => {
        setJob(started)
        if (started.done && started.error === null) setStep('install')
      },
      (error: unknown) => {
        setProblem(message(error))
        setStep('start')
      },
    )
  }

  const downloadZip = () => {
    api.zip().then(
      (blob) => {
        save(blob, ZIP_NAME)
      },
      (error: unknown) => {
        setProblem(message(error))
      },
    )
  }

  const canGoBack = step === 'start' || step === 'firmware' || step === 'films'

  return (
    <PageFrame subtitle="Installer">
      <main className="mx-auto max-w-3xl space-y-10 px-4 py-10">
        <Timeline
          steps={flow.map((id) => LABELS[id])}
          current={flow.indexOf(step)}
          onBack={
            canGoBack
              ? (index) => {
                  setStep(flow[index] ?? 'start')
                }
              : null
          }
        />

        {problem && (
          <p role="alert" className="border-ink border-l-4 pl-3 text-sm">
            {problem}
          </p>
        )}

        {step === 'start' && (
          <StartStep
            zip={zip}
            onZip={setZip}
            cards={cards}
            card={card}
            onCard={setCard}
            onNext={() => {
              setStep('firmware')
            }}
            ready={build !== null && (zip || card !== '')}
          />
        )}
        {step === 'firmware' && (
          <FirmwareStep
            firmware={firmware}
            onFirmware={setFirmware}
            onBack={() => {
              setStep('start')
            }}
            onNext={() => {
              if (firmware === 'original') startBuild(false)
              else setStep('films')
            }}
          />
        )}
        {step === 'films' && (
          <FilmsStep
            zip={zip}
            looks={looks}
            customizing={customizing}
            onCustomize={setCustomizing}
            onBuild={startBuild}
            onBack={() => {
              setStep('firmware')
            }}
          />
        )}
        {step === 'build' && (
          <BuildStep
            job={job}
            firmware={firmware}
            onRetry={() => {
              startBuild(lastCustom)
            }}
            onBack={() => {
              setStep(firmware === 'original' ? 'firmware' : 'films')
            }}
          />
        )}
        {step === 'install' && job && (
          <InstallStep
            job={job}
            cardName={cards.find((c) => c.path === job.card && c.name !== '')?.name ?? 'SD card'}
            changed={changedSlot(looks.items)}
            onZip={downloadZip}
            onRestart={() => {
              setJob(null)
              setCustomizing(false)
              setStep('start')
            }}
          />
        )}
      </main>
    </PageFrame>
  )
}
