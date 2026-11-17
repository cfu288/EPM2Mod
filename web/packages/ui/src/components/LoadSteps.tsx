import { CARD_NAME } from '../lib/lookfile'

/** How to load the look file on the camera. `copied`: the file is on the card already, so the copy step is left out. */
export function LoadSteps({ copied = false }: { copied?: boolean }) {
  return (
    <>
      <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm">
        {!copied && <li>Copy {CARD_NAME} to the top folder of the SD card.</li>}
        <li>
          On the camera, press MENU and find the gears tab (Custom Menu). If it is hidden, turn it on in Setup Menu →
          Menu Display.
        </li>
        <li>MENU → Custom Menu → J → Load Looks → Load → OK.</li>
        <li>
          The Load Looks row shows Loaded, and the ART menu shows your films. They stay after you switch the camera off.
        </li>
      </ol>
      <p className="text-ink-soft mt-3 text-sm">
        To go back to the films built into the firmware: MENU → Custom Menu → J → Load Looks → Built-in → OK.
      </p>
    </>
  )
}
