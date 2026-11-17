import { useEffect, useState } from 'react'
import { ArrowDownTrayIcon, ArrowPathIcon } from '@heroicons/react/20/solid'
import {
  CARD_NAME,
  choicesOf,
  filmById,
  LoadSteps,
  MenuEditor,
  PageFrame,
  REPO,
  slots,
  StripPreview,
  useLooks,
} from '@epm2mod/ui'
import { api, type Build, type Card, type Job } from './api'

const ZIP_NAME = 'EPM2Mod-card.zip'
const RESTORE = `${REPO}/blob/main/docs/install.md#restore-original-firmware`
const FEATURES = `${REPO}#added-features`

/** The stages a user sees, and the step of the build (`epm2mod make`, steps 1 to 5) that ends each one. */
const STAGES = [
  { label: "Download Olympus's firmware and check it", step: 1 },
  { label: 'Add the EPM2Mod changes', step: 3 },
  { label: 'Check the result against the tested build', step: 4 },
  { label: 'Write the files', step: 5 },
]

function save(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = name
  link.click()
  URL.revokeObjectURL(url)
}

const message = (error: unknown) => (error instanceof Error ? error.message : String(error))

/** The films of ART 1 to 12 when no look file is loaded, from the film records. */
function BuiltInFilms() {
  return (
    <>
      <p className="text-ink-soft mt-4 text-sm">The firmware puts these films in ART 1 to 12:</p>
      <ol className="divide-rule border-rule mt-3 grid grid-cols-1 border-y text-sm sm:grid-cols-2 sm:gap-x-8">
        {slots.map((slot) => (
          <li key={slot.art} className="border-rule flex gap-x-3 border-b py-2">
            <span className="text-muted w-12 shrink-0">ART {slot.art}</span>
            {filmById(slot.builtIn).film}
          </li>
        ))}
      </ol>
    </>
  )
}

/** How to put the firmware on the camera after it is made. */
function UpdateSteps({ zip, looks }: { zip: boolean; looks: boolean }) {
  return (
    <section aria-labelledby="update-heading">
      <h2 id="update-heading" className="section-title border-t-[6px] pt-4 text-lg">
        Update the camera
      </h2>
      <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm">
        {zip ? (
          <>
            <li>
              Open {ZIP_NAME}. It holds the folder DCOLYMP{looks ? ` and the file ${CARD_NAME}` : ''}.
            </li>
            <li>
              Copy {looks ? 'both' : 'the folder'} to the top folder of the SD card, beside DCIM. Replace the DCOLYMP
              folder if the card has one.
            </li>
          </>
        ) : (
          <li>Eject the SD card from this computer and take it out.</li>
        )}
        <li>Charge the camera's battery fully.</li>
        <li>Put the card in the camera. With the camera off, hold OK and switch the camera on.</li>
        <li>
          An orange lamp lights while the camera writes the firmware, for 1 to 2 minutes. Keep the camera on until the
          lamp blinks.
        </li>
        <li>When the lamp blinks, the update is done. Switch the camera off and on again.</li>
        <li>To check: the ART menu shows film names, such as {filmById(slots[0]?.builtIn ?? '').name}.</li>
      </ol>
      {looks && (
        <>
          <h3 className="mt-6 text-sm font-bold">Then load your films</h3>
          <LoadSteps copied />
        </>
      )}
      <p className="text-ink-soft mt-4 text-sm">
        <a className="hover:text-ink underline" href={RESTORE}>
          How to go back to Olympus's firmware
        </a>
      </p>
    </section>
  )
}

/** The job's stages with a mark for each one that is done, and the full lines of the build tool under Details. */
function Progress({ job }: { job: Job }) {
  return (
    <section aria-labelledby="progress-heading">
      <h2 id="progress-heading" className="section-title border-t-[6px] pt-4 text-lg">
        Progress
      </h2>
      <ol aria-live="polite" className="mt-3 space-y-1 text-sm">
        {STAGES.map((stage) => {
          const done = job.step >= stage.step && (stage.step < job.steps || (job.done && job.error === null))
          return (
            <li key={stage.step} className={done ? '' : 'text-muted'}>
              {done ? '✓' : '·'} {stage.label}
            </li>
          )
        })}
      </ol>
      {job.error && (
        <p role="alert" className="border-ink mt-3 border-l-4 pl-3 text-sm whitespace-pre-wrap">
          Stopped: {job.error}
        </p>
      )}
      <details className="mt-3 text-xs">
        <summary className="text-ink-soft cursor-pointer">Details</summary>
        <ol className="mt-2 space-y-1 font-mono break-words whitespace-pre-wrap">
          {job.lines.map((line, index) => (
            <li key={index}>{line}</li>
          ))}
        </ol>
      </details>
    </section>
  )
}

export default function App() {
  const looks = useLooks()
  const [withLooks, setWithLooks] = useState(false)
  const [build, setBuild] = useState<Build | null>(null)
  const [cards, setCards] = useState<Card[]>([])
  const [output, setOutput] = useState<'card' | 'zip'>('card')
  const [card, setCard] = useState('')
  const [job, setJob] = useState<Job | null>(null)
  const [problem, setProblem] = useState<string | null>(null)
  const running = job !== null && !job.done

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

  useEffect(() => {
    if (!running) return
    const timer = window.setInterval(() => {
      api.job().then(setJob, (error: unknown) => {
        setProblem(message(error))
      })
    }, 500)
    return () => {
      window.clearInterval(timer)
    }
  }, [running])

  const start = () => {
    setProblem(null)
    api
      .make(withLooks ? choicesOf(looks.items) : [], output === 'card' ? card : null)
      .then(setJob, (error: unknown) => {
        setProblem(message(error))
      })
  }

  const canStart = !running && build !== null && (output === 'zip' || card !== '')
  const made = job?.done === true && job.error === null ? job : null

  return (
    <PageFrame subtitle="Installer">
      <div className="bg-ink text-white">
        <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8 lg:py-16">
          <h1 className="font-display max-w-4xl text-4xl font-extrabold tracking-tight sm:text-5xl">
            Install EPM2Mod on your <span className="whitespace-nowrap">PEN E-PM2</span>
          </h1>
          <p className="text-rule mt-6 max-w-3xl text-lg">
            EPM2Mod is unofficial firmware for the Olympus PEN E-PM2, made by independent developers. It adds film
            looks, interval shooting, a level gauge and focus peaking.
          </p>
          <p className="text-rule mt-3 max-w-3xl text-lg">
            This page builds it on your computer: it downloads Olympus's firmware from OM Digital Solutions, adds the
            EPM2Mod changes and checks the result. Then it writes the files to your SD card, or gives you a zip.
          </p>
          <p className="text-rule mt-6 text-sm">
            You can go back to Olympus's firmware at any time:{' '}
            <a className="underline hover:text-white" href={RESTORE}>
              how to go back
            </a>
            .{' '}
            {build && (
              <>
                Firmware build {build.name} (
                <a className="underline hover:text-white" href={FEATURES}>
                  what it adds
                </a>
                ).
              </>
            )}
          </p>
        </div>
      </div>

      <main className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-12 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <section aria-labelledby="looks-heading">
              <h2 id="looks-heading" className="section-title">
                Film looks
              </h2>
              <div className="mt-4 flex items-start gap-x-3">
                <input
                  id="with-looks"
                  type="checkbox"
                  aria-describedby="with-looks-hint"
                  checked={withLooks}
                  onChange={(event) => {
                    setWithLooks(event.target.checked)
                  }}
                  className="accent-ink mt-1 size-4"
                />
                <div>
                  <label htmlFor="with-looks" className="font-bold">
                    Choose the films in the ART menu
                  </label>
                  <p id="with-looks-hint" className="text-ink-soft text-sm">
                    After the firmware update, you load your films from a camera menu. This page shows the steps when
                    the files are ready.
                  </p>
                </div>
              </div>
              {!withLooks && <BuiltInFilms />}
            </section>
            {withLooks && (
              <div className="mt-14">
                <MenuEditor looks={looks} />
              </div>
            )}
          </div>

          <aside className="contents lg:sticky lg:top-8 lg:block lg:space-y-8 lg:self-start">
            {withLooks && (
              <div className="order-first lg:order-none">
                <StripPreview art={looks.selected + 1} filmId={looks.items[looks.selected]?.filmId ?? null} />
              </div>
            )}
            <div className="space-y-8">
              <fieldset>
                <legend className="section-title w-full border-t-[6px] pt-4 text-lg">Where the files go</legend>
                <div className="mt-3 space-y-3 text-sm">
                  <label className="flex items-center gap-x-3">
                    <input
                      type="radio"
                      name="output"
                      checked={output === 'card'}
                      onChange={() => {
                        setOutput('card')
                      }}
                      className="accent-ink size-4"
                    />
                    Write to an SD card
                  </label>
                  <p className="text-ink-soft pl-7">
                    Your photos stay on the card: this adds the firmware file{withLooks ? ` and ${CARD_NAME}` : ''}.
                  </p>
                  {output === 'card' && (
                    <div className="space-y-2 pl-7">
                      {cards.length > 0 ? (
                        <select
                          aria-label="SD card"
                          value={card}
                          onChange={(event) => {
                            setCard(event.target.value)
                          }}
                          className="border-ink w-full border bg-white px-2 py-2"
                        >
                          {cards.map((c) => (
                            <option key={c.path} value={c.path}>
                              {c.label}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <p className="text-ink-soft">Put the camera's SD card in this computer, then select Refresh.</p>
                      )}
                      <button type="button" onClick={refreshCards} className="btn py-1.5">
                        <ArrowPathIcon aria-hidden="true" className="size-4" />
                        Refresh
                      </button>
                    </div>
                  )}
                  <label className="flex items-center gap-x-3">
                    <input
                      type="radio"
                      name="output"
                      checked={output === 'zip'}
                      onChange={() => {
                        setOutput('zip')
                      }}
                      className="accent-ink size-4"
                    />
                    Download a zip to copy to the card yourself
                  </label>
                </div>
              </fieldset>

              <button
                type="button"
                disabled={!canStart}
                onClick={start}
                className="btn bg-ink hover:text-ink disabled:bg-rule w-full justify-between py-3 text-base text-white hover:bg-white"
              >
                {running ? 'Making the firmware…' : 'Make firmware'}
              </button>

              {problem && (
                <p role="alert" className="border-ink border-l-4 pl-3 text-sm">
                  {problem}
                </p>
              )}

              {job && <Progress job={job} />}

              {made && (
                <>
                  {made.card === null ? (
                    <button
                      type="button"
                      onClick={() => {
                        api.zip().then(
                          (blob) => {
                            save(blob, ZIP_NAME)
                          },
                          (error: unknown) => {
                            setProblem(message(error))
                          },
                        )
                      }}
                      className="btn bg-ink hover:text-ink w-full justify-between py-3 text-base text-white hover:bg-white"
                    >
                      Download {ZIP_NAME}
                      <ArrowDownTrayIcon aria-hidden="true" className="size-5" />
                    </button>
                  ) : (
                    <p className="text-sm font-bold">Done: the files are on the card.</p>
                  )}
                  <UpdateSteps zip={made.card === null} looks={made.files.includes(CARD_NAME)} />
                </>
              )}
            </div>
          </aside>
        </div>
      </main>
    </PageFrame>
  )
}
