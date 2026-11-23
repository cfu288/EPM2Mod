import { useCallback, useEffect, useId, useReducer, useState, type ReactNode } from 'react'
import { ArrowDownTrayIcon, ArrowPathIcon } from '@heroicons/react/20/solid'
import {
  choicesOf,
  FilmCredit,
  MenuEditor,
  PageFrame,
  presetSlots,
  save,
  StripPreview,
  useLooks,
  type Looks,
} from '@epm2mod/ui'
import { api, type Build, type Card, type Firmware, type Job } from './api'
import { FLOWS, initial, labels, onTimeline, reduce, startReady } from './flow'
import { Timeline } from './Timeline'

const ZIP_NAME = 'EPM2Mod-card.zip'

const HELP = 'https://github.com/cfu288/EPM2Mod/blob/main/docs/user/install.md'

/** A card in the list: its name, size and where it is mounted. */
const cardLabel = (c: Card) => `${c.name || 'SD card'} · ${String(Math.round(c.size / 1e9))} GB · ${c.path}`
const DEFAULT_CHOICES = choicesOf(presetSlots())

/** What the user sees while the job runs, and the step of the job (`steps` of `epm2mod serve`) that ends each one. */
function stages(job: Job | null, firmware: Firmware) {
  const write = job?.card == null ? 'Prepare the zip' : 'Write to the SD card'
  if (firmware === 'films') return [{ label: write, step: 1 }]
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
      title="Where to put the files"
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
                <p className="text-ink-soft">
                  If your computer has no card slot, connect the camera by USB and select Storage on the camera.
                </p>
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
      title="Choose what to install"
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
          line="Install the EPM2Mod firmware and film simulations."
          checked={props.firmware === 'epm2mod'}
          onChoose={() => {
            props.onFirmware('epm2mod')
          }}
        />
        <Choice
          group="firmware"
          title="Film simulations only"
          line="Install film simulations (only if EPM2Mod is already installed)."
          checked={props.firmware === 'films'}
          onChoose={() => {
            props.onFirmware('films')
          }}
        />
        <Choice
          group="firmware"
          title="Olympus original"
          line="Revert to the stock firmware."
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
  /** Only the film file is written: the editor opens at once, for a camera that has film simulations already. */
  only: boolean
  looks: Looks
  customizing: boolean
  onCustomize: (on: boolean) => void
  onBuild: (custom: boolean) => void
  onBack: () => void
}) {
  if (!props.customizing && !props.only)
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
      title={props.only ? 'Choose the film simulations' : 'Customize the film simulations'}
      actions={
        <>
          <BackButton
            onClick={() => {
              if (props.only) props.onBack()
              else props.onCustomize(false)
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
      {props.only && <p>This list replaces the film simulations on the camera.</p>}
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
  const title = { original: 'Getting the original firmware', epm2mod: 'Building', films: 'Writing' }[props.firmware]
  const failedTitle =
    doneCount === list.length - 1
      ? job?.card == null
        ? 'Could not make the zip'
        : 'Could not write to the card'
      : doneCount === 0
        ? 'Could not download the firmware'
        : 'The firmware could not be made'
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
          {props.firmware !== 'films' && 'This takes about a minute. '}
          {job?.card != null && 'Do not take the card out.'}
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
  const films = job.firmware === 'films'
  const what = { original: "Olympus's original firmware is", epm2mod: 'EPM2Mod is', films: 'The film simulations are' }[
    job.firmware
  ]
  const flash = job.camera_steps.findIndex((step) => step.id === 'flash') + 1
  return (
    <Step
      title={films ? 'Load on the camera' : 'Install on the camera'}
      actions={
        <>
          <button type="button" onClick={props.onRestart} className={secondary}>
            Start over
          </button>
          <button type="button" onClick={props.onFinish} className={primary}>
            Close the installer
          </button>
        </>
      }
    >
      <p className="font-bold">
        {zip ? 'The zip is ready.' : `${what} on the SD card${props.cardName ? ` ${props.cardName}` : ''}.`}
      </p>
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
        {films
          ? 'If there is no Load Looks row, install EPM2Mod first.'
          : `If the camera starts normally, turn it off and do step ${String(flash)} again.`}{' '}
        <a className="hover:text-ink underline" href={HELP}>
          Install guide
        </a>
      </p>
    </Step>
  )
}

export default function App() {
  const looks = useLooks(presetSlots)
  const [state, dispatch] = useReducer(reduce, initial)
  const [build, setBuild] = useState<Build | null>(null)
  const [cards, setCards] = useState<Card[]>([])
  const { step, firmware, zip, card, job, problem } = state
  const running = job !== null && !job.done
  const flow = FLOWS[firmware]
  const fail = (error: unknown) => {
    dispatch({ type: 'problem', problem: message(error) })
  }
  const go = (to: (typeof flow)[number]) => {
    dispatch({ type: 'go', step: to })
  }

  const refreshCards = useCallback(() => {
    api.cards().then(
      (found) => {
        setCards(found)
        dispatch({ type: 'cards', cards: found })
      },
      (error: unknown) => {
        dispatch({ type: 'problem', problem: message(error) })
      },
    )
  }, [])

  useEffect(() => {
    api.build().then(setBuild, (error: unknown) => {
      dispatch({ type: 'problem', problem: message(error) })
    })
    refreshCards()
  }, [refreshCards])

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
  }, [searching, refreshCards])

  useEffect(() => {
    if (!running) return
    const timer = window.setInterval(() => {
      api.job().then((next) => {
        dispatch({ type: 'job', job: next })
      }, fail)
    }, 500)
    return () => {
      window.clearInterval(timer)
    }
  }, [running])

  const startBuild = (custom: boolean) => {
    // the firmware has Olympus's art filters: every EPM2Mod install gets a look file, loaded with Load Looks
    const wanted = firmware === 'original' ? [] : custom ? choicesOf(looks.items) : DEFAULT_CHOICES
    dispatch({ type: 'make', custom })
    api.make(firmware, wanted, zip ? null : card).then(
      (started) => {
        dispatch({ type: 'job', job: started })
      },
      (error: unknown) => {
        dispatch({ type: 'refused', problem: message(error) })
      },
    )
  }

  const downloadZip = () => {
    api.zip().then((blob) => {
      save(blob, ZIP_NAME)
    }, fail)
  }

  if (state.finished)
    return (
      <PageFrame subtitle="Installer">
        <main className="mx-auto max-w-3xl px-4 py-10">
          <Step title="The installer is finished">
            <p>You can close this tab.</p>
          </Step>
        </main>
      </PageFrame>
    )

  return (
    <PageFrame subtitle="Installer">
      <main className="mx-auto max-w-3xl space-y-10 px-4 py-10">
        <Timeline
          steps={labels(firmware)}
          current={flow.indexOf(step)}
          canGo={(index) => {
            const to = flow[index]
            return to !== undefined && onTimeline(state, to)
          }}
          onGo={(index) => {
            const to = flow[index]
            if (to) go(to)
          }}
        />

        {problem && (
          <p role="alert" className="border-ink border-l-4 pl-3 text-sm">
            {problem}
          </p>
        )}

        {step === 'start' && (
          <StartStep
            zip={zip}
            onZip={(on) => {
              dispatch({ type: 'zip', zip: on })
            }}
            cards={cards}
            card={card}
            onCard={(path) => {
              dispatch({ type: 'card', card: path })
            }}
            onNext={() => {
              go('firmware')
            }}
            ready={build !== null && startReady(state)}
          />
        )}
        {step === 'firmware' && (
          <FirmwareStep
            firmware={firmware}
            onFirmware={(next) => {
              dispatch({ type: 'firmware', firmware: next })
            }}
            onBack={() => {
              go('start')
            }}
            onNext={() => {
              if (firmware === 'original') startBuild(false)
              else go('films')
            }}
          />
        )}
        {step === 'films' && (
          <FilmsStep
            zip={zip}
            only={firmware === 'films'}
            looks={looks}
            customizing={state.customizing}
            onCustomize={(on) => {
              dispatch({ type: 'customize', on })
            }}
            onBuild={startBuild}
            onBack={() => {
              go('firmware')
            }}
          />
        )}
        {step === 'build' && (
          <BuildStep
            job={job}
            firmware={firmware}
            onRetry={() => {
              startBuild(state.lastCustom)
            }}
            onBack={() => {
              go(firmware === 'original' ? 'firmware' : 'films')
            }}
          />
        )}
        {step === 'install' && job && (
          <InstallStep
            job={job}
            cardName={cards.find((c) => c.path === job.card && c.name !== '')?.name ?? ''}
            onZip={downloadZip}
            onFinish={() => {
              api.quit().then(() => {
                // the browser opened this tab, so it lets the page close it; the message is for a browser that does not
                window.close()
                dispatch({ type: 'finished' })
              }, fail)
            }}
            onRestart={() => {
              dispatch({ type: 'restart' })
            }}
          />
        )}
      </main>
    </PageFrame>
  )
}
