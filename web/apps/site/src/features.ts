/** The camera features of the mod: the home page lists them, the features page explains them. */
export interface Feature {
  id: string
  name: string
  /** One sentence: why a user wants it. */
  summary: string
  /** Each step is one action on the camera. */
  steps: string[]
  /** Camera screens under public/ui/. */
  screens: { src: string; alt: string }[]
}

export const features: Feature[] = [
  {
    id: 'film-looks',
    name: 'Film simulations',
    summary: 'Film colours straight out of the camera.',
    steps: [
      'Install EPM2Mod with the installer. It puts the film simulations on the SD card.',
      'MENU → SETUP → Custom Menu → J → Load Looks → Load. Until then the camera has the Olympus art filters.',
      'Press OK, select Picture Mode, and scroll right past Custom.',
    ],
    screens: [{ src: 'ui/quick-menu-portra.png', alt: 'The quick menu with Picture Mode on Portra 400' }],
  },
  {
    id: 'interval',
    name: 'Interval shooting',
    summary: 'Time-lapses without a remote.',
    steps: [
      'Press MENU, select P on the first screen, and press OK. Set the camera clock.',
      'MENU → SETUP → Shooting Menu 2 → Time Lapse Settings → On. Set the frames and the interval.',
      'For a film simulation, press OK → Picture Mode and pick one.',
      'Press the shutter button to start.',
    ],
    screens: [
      { src: 'ui/shooting-menu-2.png', alt: 'Shooting Menu 2 with Time Lapse Settings' },
      { src: 'ui/time-lapse-settings.png', alt: 'The Time Lapse Settings screen' },
    ],
  },
  {
    id: 'level',
    name: 'Level gauge',
    summary: 'Keep horizons straight.',
    steps: [
      'MENU → SETUP → Custom Menu → D → Info Settings → LV-Info → Level Gauge.',
      'In live view, press INFO until the bars appear.',
      'To calibrate, put the camera flat, then MENU → SETUP → Custom Menu → J → Level Adjust → Adjust.',
    ],
    screens: [
      { src: 'ui/level-gauge.png', alt: 'The level gauge in live view' },
      { src: 'ui/level-adjust.png', alt: 'Level Adjust with Adjust selected' },
    ],
  },
  {
    id: 'peaking',
    name: 'Focus peaking',
    summary: 'Easier manual focus, with any lens.',
    steps: [
      'Set the focus mode to MF: the lines show in live view.',
      'To change the colour: MENU → SETUP → Custom Menu → A → Peaking.',
      'To also zoom in when you turn the focus ring: MENU → SETUP → Custom Menu → A → MF Assist → On.',
    ],
    screens: [{ src: 'ui/peaking-list.png', alt: 'Custom Menu A with the Peaking list' }],
  },
  {
    id: 'lowest-ss',
    name: 'Lowest shutter speed',
    summary: 'Sharp moving subjects, or less noise on still ones, in dim light.',
    steps: [
      'Set the shooting mode to P or A, and ISO to Auto.',
      'MENU → SETUP → Custom Menu → E. Exp/▣/ISO → Lowest S/S Setting.',
      'Press RIGHT, choose a speed with UP/DOWN, and press OK.',
    ],
    screens: [
      { src: 'ui/lowest-ss-row.png', alt: 'Custom Menu E with the Lowest S/S Setting row' },
      { src: 'ui/lowest-ss-list.png', alt: 'Lowest S/S Setting set to 1/15' },
    ],
  },
]
