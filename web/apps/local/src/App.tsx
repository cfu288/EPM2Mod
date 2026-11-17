import { useEffect, useState } from 'react'
import { ArrowDownTrayIcon, ArrowPathIcon } from '@heroicons/react/20/solid'
import { CARD_NAME, choicesOf, MenuEditor, PageFrame, REPO, StripPreview, useLooks } from '@epm2mod/ui'
import { api, type Build, type Card, type Job } from './api'

const ZIP_NAME = 'EPM2Mod-card.zip'
const RESTORE = `${REPO}/blob/main/docs/install.md#restore-original-firmware`

/** The stages shown while the firmware is made, and the step of `epm2mod make` (1 to 5) that ends each one. */
const stages = (zip: boolean) => [
  { label: "Download Olympus's firmware", step: 1 },
  { label: 'Add EPM2Mod', step: 3 },
  { label: 'Check the result', step: 4 },
  { label: zip ? 'Prepare the zip' : 'Write to the SD card', step: 5 },
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

function Progress({ job }: { job: Job }) {
  return (
    <section aria-label="Progress">
      <ol aria-live="polite" className="space-y-1 text-sm">
        {stages(job.card === null).map((stage) => {
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
          {job.error}
        </p>
      )}
    </section>
  )
}

function UpdateSteps({ zip, looks }: { zip: boolean; looks: boolean }) {
  return (
    <section aria-label="Update the camera">
      <ol className="list-decimal space-y-1 pl-5 text-sm">
        {zip && <li>Copy DCOLYMP{looks ? ` and ${CARD_NAME}` : ''} from the zip to the card.</li>}
        <li>Put the card in the camera. Charge the battery.</li>
        <li>Camera off: hold OK and switch it on.</li>
        <li>When the orange lamp blinks (1 to 2 minutes), switch the camera off and on.</li>
        {looks && <li>MENU → Custom Menu → J → Load Looks → Load.</li>}
      </ol>
    </section>
  )
}

export default function App() {
  const looks = useLooks()
  const [withLooks, setWithLooks] = useState(false)
  const [build, setBuild] = useState<Build | null>(null)
  const [cards, setCards] = useState<Card[]>([])
  const [target, setTarget] = useState('') // a card's path, or '' for the zip
  const [job, setJob] = useState<Job | null>(null)
  const [problem, setProblem] = useState<string | null>(null)
  const running = job !== null && !job.done

  const refreshCards = () => {
    api.cards().then(
      (found) => {
        setCards(found)
        setTarget((current) => (found.some((c) => c.path === current) ? current : (found[0]?.path ?? '')))
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
    api.make(withLooks ? choicesOf(looks.items) : [], target || null).then(setJob, (error: unknown) => {
      setProblem(message(error))
    })
  }

  const made = job?.done === true && job.error === null ? job : null

  return (
    <PageFrame subtitle="Installer">
      <main className="mx-auto max-w-2xl space-y-8 px-4 py-10">
        <h1 className="font-display text-3xl font-extrabold tracking-tight">Install EPM2Mod</h1>

        <div className="flex items-center gap-x-2">
          <select
            aria-label="Write to"
            value={target}
            onChange={(event) => {
              setTarget(event.target.value)
            }}
            className="border-ink min-w-0 flex-1 border bg-white px-2 py-2 text-sm"
          >
            {cards.map((c) => (
              <option key={c.path} value={c.path}>
                {c.label}
              </option>
            ))}
            <option value="">Download a zip</option>
          </select>
          <button type="button" aria-label="Find SD cards" onClick={refreshCards} className="btn px-2.5">
            <ArrowPathIcon aria-hidden="true" className="size-4" />
          </button>
        </div>

        <div>
          <label className="flex items-center gap-x-3 text-sm">
            <input
              type="checkbox"
              checked={withLooks}
              onChange={(event) => {
                setWithLooks(event.target.checked)
              }}
              className="accent-ink size-4"
            />
            Customize the films in the ART menu
          </label>
          {withLooks && (
            <div className="mt-6 space-y-8">
              <StripPreview art={looks.selected + 1} filmId={looks.items[looks.selected]?.filmId ?? null} />
              <MenuEditor looks={looks} />
            </div>
          )}
        </div>

        <button
          type="button"
          disabled={running || build === null}
          onClick={start}
          className="btn bg-ink hover:text-ink disabled:bg-rule w-full justify-center py-3 text-base text-white hover:bg-white"
        >
          {running ? 'Building…' : 'Build custom firmware'}
        </button>

        {problem && (
          <p role="alert" className="border-ink border-l-4 pl-3 text-sm">
            {problem}
          </p>
        )}
        {job && <Progress job={job} />}

        {made && (
          <div className="space-y-4">
            {made.card === null && (
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
                className="btn bg-ink hover:text-ink w-full justify-center py-3 text-base text-white hover:bg-white"
              >
                <ArrowDownTrayIcon aria-hidden="true" className="size-5" />
                Download {ZIP_NAME}
              </button>
            )}
            <UpdateSteps zip={made.card === null} looks={made.files.includes(CARD_NAME)} />
          </div>
        )}

        <p className="text-muted text-xs">
          {build?.name}
          {build && ' · '}
          <a className="hover:text-ink underline" href={RESTORE}>
            Restore Olympus firmware
          </a>
        </p>
      </main>
    </PageFrame>
  )
}
