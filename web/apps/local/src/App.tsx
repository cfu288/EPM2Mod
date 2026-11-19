import { useEffect, useId, useState, type ReactNode } from 'react'
import { ArrowDownTrayIcon, ArrowPathIcon } from '@heroicons/react/20/solid'
import { choicesOf, FilmCredit, MenuEditor, PageFrame, StripPreview, useLooks, type Looks } from '@epm2mod/ui'
import { api, type Build, type Card, type Firmware, type Job } from './api'
import { presetSlots } from './preset'
import { Timeline } from './Timeline'

type StepId = 'start' | 'firmware' | 'films' | 'build' | 'install'
const LABELS: Record<StepId, string> = {
  start: 'Start',
  firmware: 'Firmware',
  films: 'Film simulations',
  build: 'Build',
  install: 'Install',
}
/** The steps of each choice of firmware: Olympus's own has no film looks. */
const FLOWS: Record<Firmware, StepId[]> = {
  epm2mod: ['start', 'firmware', 'films', 'build', 'install'],
  original: ['start', 'firmware', 'build', 'install'],
}
const ZIP_NAME = 'EPM2Mod-card.zip'

const HELP = 'https://github.com/cfu288/EPM2Mod/blob/main/docs/user/install.md'

/** A card in the list: its name, size and where it is mounted. */
const cardLabel = (c: Card) => `${c.name || 'SD card'} · ${String(Math.round(c.size / 1e9))} GB · ${c.path}`
const DEFAULT_CHOICES = choicesOf(presetSlots())

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
  line?: string
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
          aria-describedby={props.line ? `${id}-line` : undefined}
          checked={props.checked}
          onChange={props.onChoose}
          className="accent-ink mt-1 size-4"
        />
        <div>
          <label htmlFor={id} className="block cursor-pointer font-bold">
            {props.title}
          </label>
          {props.line && (
            <p id={`${id}-line`} className="text-ink-soft text-sm">
              {props.line}
            </p>
          )}
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
      title="Install firmware"
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
                  {props.card === '' && <option value="" disabled />}
                  {props.cards.map((c) => (
                    <option key={c.path} value={c.path}>
                      {cardLabel(c)}
                    </option>
                  ))}
                </select>
                {props.cards.length > 1 && (
                  <p className="text-ink-soft">
                    To find the camera&apos;s card, take it out and see which entry goes away.
                  </p>
                )}
              </>
            ) : (
              <>
                <p className="flex items-center gap-x-2">
                  <ArrowPathIcon aria-hidden="true" className="size-4 animate-spin" />
                  Insert the camera&apos;s SD card.
                </p>
                <p className="text-ink-soft">No card slot? Connect the camera by USB and choose Storage on it.</p>
              </>
            )}
          </div>
        </Choice>
        <Choice
          group="output"
          title="Download a zip"
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
          line="Film simulations, interval shooting, level gauge, focus peaking, lowest shutter speed."
          checked={props.firmware === 'epm2mod'}
          onChoose={() => {
            props.onFirmware('epm2mod')
          }}
        />
        <Choice
          group="firmware"
          title="Olympus original"
          line="Removes EPM2Mod."
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
        title="Film simulations"
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
              Use the default film simulations
            </button>
          </>
        }
      >
        <p>EPM2Mod replaces the 12 art filters with film simulations.</p>
        <FilmCredit />
      </Step>
    )
  const { looks } = props
  return (
    <Step
      title="Customize the film simulations"
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
              if (window.confirm('Discard your changes and use the default film simulations?')) looks.reset()
            }}
            className={secondary}
          >
            Reset to the default film simulations
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
          About a minute.
          {job?.card != null && ' Keep the card in.'}
        </p>
      )}
    </Step>
  )
}

/** The steps on the camera come from the server (`epm2mod serve`), the same as the command line prints. */
function InstallStep(props: {
  job: Job
  cardName: string
  onZip: () => void
  onRestart: () => void
  onFinish: () => void
}) {
  const { job } = props
  const zip = job.card === null
  const what = job.firmware === 'original' ? "Olympus's original firmware" : 'EPM2Mod'
  const flash = job.camera_steps.findIndex((step) => step.id === 'flash') + 1
  return (
    <Step
      title="Install on the camera"
      actions={
        <>
          <button type="button" onClick={props.onRestart} className={secondary}>
            Start over
          </button>
          <button type="button" onClick={props.onFinish} className={primary}>
            Finish
          </button>
        </>
      }
    >
      <p className="font-bold">{zip ? 'Done.' : `Done: ${what} is on ${props.cardName}.`}</p>
      {zip && (
        <button type="button" onClick={props.onZip} className={`${primary} w-full`}>
          <ArrowDownTrayIcon aria-hidden="true" className="size-5" />
          Download {ZIP_NAME}
        </button>
      )}
      <ol aria-label="Install steps" className="list-decimal space-y-2 pl-5">
        {job.camera_steps.map((step) => (
          <li key={step.id}>{step.text}</li>
        ))}
      </ol>
      <p className="text-ink-soft text-sm">
        Camera started normally? Turn it off and repeat step {flash}.{' '}
        <a className="hover:text-ink underline" href={HELP}>
          Other problem?
        </a>
      </p>
    </Step>
  )
}

export default function App() {
  const looks = useLooks(presetSlots)
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
  const [finished, setFinished] = useState(false)
  const running = job !== null && !job.done
  const flow = FLOWS[firmware]

  const refreshCards = () => {
    api.cards().then(
      (found) => {
        setCards(found)
        // a card is chosen for the user only when it is the only one
        setCard((current) =>
          found.some((c) => c.path === current) ? current : found.length === 1 ? (found[0]?.path ?? '') : '',
        )
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

  // tell the server the page is open; it stops a few minutes after the page is closed
  useEffect(() => {
    const timer = window.setInterval(() => {
      api.ping().catch(() => undefined)
    }, 10000)
    return () => {
      window.clearInterval(timer)
    }
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
    // the firmware has Olympus's art filters: every EPM2Mod install gets a look file, loaded with Load Looks
    const wanted = firmware === 'epm2mod' ? (custom ? choicesOf(looks.items) : DEFAULT_CHOICES) : []
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

  if (finished)
    return (
      <PageFrame subtitle="Installer">
        <main className="mx-auto max-w-3xl px-4 py-10">
          <Step title="The installer is finished">
            <p>Close this tab and the window that started the installer.</p>
          </Step>
        </main>
      </PageFrame>
    )

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
            onZip={downloadZip}
            onFinish={() => {
              api.quit().then(
                () => {
                  setFinished(true)
                },
                (error: unknown) => {
                  setProblem(message(error))
                },
              )
            }}
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
