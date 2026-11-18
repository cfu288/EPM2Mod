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
    steps: ['Set the mode dial to ART.', 'Pick a film from the list.'],
    screens: [{ src: 'ui/quick-menu-portra.png', alt: 'The quick menu with Picture Mode on Portra 400' }],
  },
  {
    id: 'card-looks',
    name: 'Swap films',
    summary: 'Change films without reflashing the camera.',
    steps: [
      'Choose films in the installer and write them to the SD card.',
      'MENU → Custom Menu → J → Load Looks → Load.',
      'To undo, select Built-in instead of Load.',
    ],
    screens: [
      { src: 'ui/load-looks-loaded.png', alt: 'Load Looks reads Loaded' },
      { src: 'ui/picture-mode-loaded.png', alt: 'The Picture Mode strip with Portra 800' },
    ],
  },
  {
    id: 'interval',
    name: 'Interval shooting',
    summary: 'Time-lapses without a remote.',
    steps: [
      'Set the mode dial to P, A, S or M, and set the camera clock.',
      'MENU → Shooting Menu 2 → Time Lapse Settings → On. Set the frames and the interval.',
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
      'MENU → Custom Menu → D → Info Settings → LV-Info → Level Gauge.',
      'In live view, press INFO until the bars appear.',
      'To calibrate, put the camera flat, then MENU → Custom Menu → J → Level Adjust → Adjust.',
    ],
    screens: [
      { src: 'ui/level-gauge.png', alt: 'The level gauge in live view' },
      { src: 'ui/level-adjust.png', alt: 'Level Adjust with Adjust selected' },
    ],
  },
  {
    id: 'peaking',
    name: 'Focus peaking',
    summary: 'Easier manual focus.',
    steps: [
      'MENU → Custom Menu → A → MF Assist → On.',
      'Set the focus mode to MF and turn the focus ring.',
      'To change the colour: MENU → Custom Menu → A → Peaking.',
    ],
    screens: [{ src: 'ui/peaking-list.png', alt: 'Custom Menu A with the Peaking list' }],
  },
]
