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
    id: 'film-simulations',
    name: 'Film simulations',
    summary: 'Film simulations replace the Olympus art filters with film looks like Portra and Ektachrome.',
    steps: [
      'Install EPM2Mod with the installer. It puts the film simulations on the SD card.',
      'MENU → SETUP → Custom Menu → J → Load Looks → Load. Until then the camera has the Olympus art filters.',
      'Press OK, select Picture Mode, and scroll right past Custom.',
    ],
    screens: [{ src: 'ui/quick-menu-portra.png', alt: 'The quick menu with Picture Mode on Portra 400' }],
  },
  {
    id: 'interval-shooting',
    name: 'Interval shooting',
    summary: 'Interval shooting takes up to 240 photos for a time-lapse without a remote.',
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
    id: 'level-gauge',
    name: 'Level gauge',
    summary: 'A level gauge helps you keep horizons straight by showing you when you are tilted.',
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
    id: 'focus-peaking',
    name: 'Focus peaking',
    summary: 'Focus peaking outlines what is in focus so manual focus is easier with any lens.',
    steps: [
      'Set the focus mode to MF: the lines show in live view.',
      'To change the color: MENU → SETUP → Custom Menu → A → Peaking.',
      'To also zoom in when you turn the focus ring: MENU → SETUP → Custom Menu → A → MF Assist → On.',
    ],
    screens: [{ src: 'ui/peaking-list.png', alt: 'Custom Menu A with the Peaking list' }],
  },
  {
    id: 'lowest-shutter-speed',
    name: 'Lowest shutter speed',
    summary: 'Lowest shutter speed sets how slow Auto ISO lets the shutter go before it raises the ISO.',
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
  {
    id: 'spot-metering',
    name: 'Spot metering at the AF point',
    summary: 'Spot metering measures the light at your AF point so an off-center subject is exposed correctly.',
    steps: [
      'MENU → SETUP → Custom Menu → E. Exp/▣/ISO → Spot Metering.',
      'Select Spot, Spot Hilight or Spot Shadow, press RIGHT, choose On, and press OK.',
      'Set metering to that spot mode, then tap the subject or move a single AF target.',
    ],
    screens: [
      { src: 'ui/spot-metering-row.png', alt: 'Custom Menu E with the Spot Metering row' },
      { src: 'ui/spot-metering-page.png', alt: 'The Spot Metering page with Spot, Spot Hilight and Spot Shadow' },
    ],
  },
  {
    id: 'light-box',
    name: 'Light Box',
    summary: 'Light Box shows two photos side by side so you can compare them.',
    steps: [
      'MENU → SETUP → Custom Menu → D → Info Settings → ▶ Info → Light Box → On.',
      'In playback, press INFO until two pictures show. RIGHT or LEFT changes the right picture, OK moves it to the left.',
      'Turn the control dial to zoom in on both pictures.',
    ],
    screens: [{ src: 'ui/light-box-info.png', alt: 'The ▶ Info list with Light Box set to On' }],
  },
  {
    id: 'art-bkt',
    name: 'ART BKT in RAW Data Edit',
    summary: 'ART BKT develops one RAW in each film simulation you choose so you can compare them in the camera.',
    steps: [
      'MENU → SETUP → Shooting Menu 2 → Bracketing → ART BKT. Highlight On without pressing OK, and press RIGHT.',
      'Set each film simulation you want to On.',
      'In playback, show a RAW photo, press OK, and select RAW Data Edit → ART BKT → Yes.',
    ],
    screens: [
      { src: 'ui/art-bkt-rows.png', alt: 'The ART BKT screen with Portra 400 and Velvia set to On' },
      { src: 'ui/art-bkt-raw-edit.png', alt: 'RAW Data Edit with Current, Custom1, Custom2, ART BKT and No' },
    ],
  },
  {
    id: 'broken-stabilizer',
    name: 'Broken image stabilizer',
    summary: 'A camera with a broken image stabilizer can start without it and without the blinking IS icon.',
    steps: [
      'In the installer, select EPM2Mod and open Other options.',
      "Select My camera's image stabilizer is broken, and install as usual.",
      'MENU → SETUP → Shooting Menu 2 → Image Stabilizer is then grayed out.',
    ],
    screens: [{ src: 'ui/image-stabilizer-gray.png', alt: 'Shooting Menu 2 with Image Stabilizer grayed out' }],
  },
]
