import { useEffect, useState, type ReactNode } from 'react'
import { ArrowDownTrayIcon, ArrowPathIcon } from '@heroicons/react/20/solid'
import {
  builtInSlots,
  CARD_NAME,
  choicesOf,
  MenuEditor,
  PageFrame,
  REPO,
  StripPreview,
  useLooks,
  type Looks,
} from '@epm2mod/ui'
import { api, type Build, type Card, type Job } from './api'
import { Timeline } from './Timeline'

const STEPS = ['Films', 'SD card', 'Build', 'Install'] as const
const ZIP_NAME = 'EPM2Mod-card.zip'
const RESTORE = `${REPO}/blob/main/docs/install.md#restore-original-firmware`
const DEFAULT_CHOICES = choicesOf(builtInSlots()).join()

/** The stages shown while the firmware is built, and the step of `epm2mod make` (1 to 5) that ends each one. */
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

const primary =
  'btn bg-ink hover:text-ink disabled:bg-rule justify-center px-6 py-3 text-base text-white hover:bg-white'
const secondary = 'btn justify-center px-6 py-3 text-base'

/** One step's page: its title, its content and its buttons. */
function Step({ title, children, actions }: { title: string; children: ReactNode; actions?: ReactNode }) {
  return (
    <section aria-labelledby="step-title" className="space-y-6">
      <h1 id="step-title" className="font-display text-3xl font-extrabold tracking-tight">
        {title}
      </h1>
      {children}
      {actions && <div className="flex flex-wrap justify-end gap-3">{actions}</div>}
    </section>
  )
}

function FilmsStep({ looks, onSkip, onNext }: { looks: Looks; onSkip: () => void; onNext: () => void }) {
  return (
    <Step
      title="Customize the ART menu"
      actions={
        <>
          <button type="button" onClick={onSkip} className={secondary}>
            Keep default films
          </button>
          <button type="button" onClick={onNext} className={primary}>
            Next
          </button>
        </>
      }
    >
      <div className="max-w-md">
        <StripPreview art={looks.selected + 1} filmId={looks.items[looks.selected]?.filmId ?? null} />
      </div>
      <MenuEditor looks={looks} />
    </Step>
  )
}

function CardStep(props: {
  cards: Card[]
  target: string
  onTarget: (target: string) => void
  onRefresh: () => void
  onBack: () => void
  onBuild: () => void
  ready: boolean
}) {
  return (
    <Step
      title="Choose the SD card"
      actions={
        <>
          <button type="button" onClick={props.onBack} className={secondary}>
            Back
          </button>
          <button type="button" disabled={!props.ready} onClick={props.onBuild} className={primary}>
            Build custom firmware
          </button>
        </>
      }
    >
      <div className="flex items-center gap-x-2">
        <select
          aria-label="Write to"
          value={props.target}
          onChange={(event) => {
            props.onTarget(event.target.value)
          }}
          className="border-ink min-w-0 flex-1 border bg-white px-2 py-2 text-sm"
        >
          {props.cards.map((c) => (
            <option key={c.path} value={c.path}>
              {c.label}
            </option>
          ))}
          <option value="">Download a zip instead</option>
        </select>
        <button type="button" aria-label="Find SD cards" onClick={props.onRefresh} className="btn px-2.5">
          <ArrowPathIcon aria-hidden="true" className="size-4" />
        </button>
      </div>
    </Step>
  )
}

function BuildStep({ job, onBack }: { job: Job | null; onBack: () => void }) {
  const failed = job?.error != null
  return (
    <Step
      title={failed ? 'The build stopped' : 'Building'}
      actions={
        failed && (
          <button type="button" onClick={onBack} className={secondary}>
            Back
          </button>
        )
      }
    >
      <ol aria-label="Progress" aria-live="polite" className="space-y-2">
        {stages(job?.card == null).map((stage) => {
          const done = job !== null && job.step >= stage.step && (stage.step < job.steps || (job.done && !failed))
          return (
            <li key={stage.step} className={done ? '' : 'text-muted'}>
              {done ? '✓' : '·'} {stage.label}
            </li>
          )
        })}
      </ol>
      {failed && (
        <p role="alert" className="border-ink border-l-4 pl-3 text-sm whitespace-pre-wrap">
          {job.error}
        </p>
      )}
    </Step>
  )
}

function InstallStep({ job, onZip, onRestart }: { job: Job; onZip: () => void; onRestart: () => void }) {
  const zip = job.card === null
  const looks = job.files.includes(CARD_NAME)
  return (
    <Step
      title="Install on the camera"
      actions={
        <button type="button" onClick={onRestart} className={secondary}>
          Start over
        </button>
      }
    >
      {zip && (
        <button type="button" onClick={onZip} className={`${primary} w-full`}>
          <ArrowDownTrayIcon aria-hidden="true" className="size-5" />
          Download {ZIP_NAME}
        </button>
      )}
      <ol aria-label="Install steps" className="list-decimal space-y-2 pl-5">
        {zip && <li>Copy DCOLYMP{looks ? ` and ${CARD_NAME}` : ''} from the zip to the card.</li>}
        <li>Put the card in the camera. Charge the battery.</li>
        <li>Camera off: hold OK and switch it on.</li>
        <li>When the orange lamp blinks (1 to 2 minutes), switch the camera off and on.</li>
        {looks && <li>MENU → Custom Menu → J → Load Looks → Load.</li>}
      </ol>
    </Step>
  )
}

export default function App() {
  const looks = useLooks()
  const [step, setStep] = useState(0)
  const [customize, setCustomize] = useState(false)
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
      api.job().then(
        (next) => {
          setJob(next)
          if (next?.done && next.error === null) setStep(3)
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

  const startBuild = () => {
    setProblem(null)
    const choices = choicesOf(looks.items)
    // films left as they are need no look file: the firmware has them built in
    const wanted = customize && choices.join() !== DEFAULT_CHOICES ? choices : []
    setJob(null)
    setStep(2)
    api.make(wanted, target || null).then(
      (started) => {
        setJob(started)
        if (started.done && started.error === null) setStep(3)
      },
      (error: unknown) => {
        setProblem(message(error))
        setStep(1)
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

  return (
    <PageFrame subtitle="Installer">
      <main className="mx-auto max-w-3xl space-y-10 px-4 py-10">
        <Timeline steps={STEPS} current={step} onBack={step < 2 ? setStep : null} />

        {problem && (
          <p role="alert" className="border-ink border-l-4 pl-3 text-sm">
            {problem}
          </p>
        )}

        {step === 0 && (
          <FilmsStep
            looks={looks}
            onSkip={() => {
              setCustomize(false)
              setStep(1)
            }}
            onNext={() => {
              setCustomize(true)
              setStep(1)
            }}
          />
        )}
        {step === 1 && (
          <CardStep
            cards={cards}
            target={target}
            onTarget={setTarget}
            onRefresh={refreshCards}
            onBack={() => {
              setStep(0)
            }}
            onBuild={startBuild}
            ready={build !== null}
          />
        )}
        {step === 2 && (
          <BuildStep
            job={job}
            onBack={() => {
              setStep(1)
            }}
          />
        )}
        {step === 3 && job && (
          <InstallStep
            job={job}
            onZip={downloadZip}
            onRestart={() => {
              setJob(null)
              setStep(0)
            }}
          />
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
