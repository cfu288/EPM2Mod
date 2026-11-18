import { useEffect } from 'react'
import { Layout } from './Layout'
import { Features } from './pages/Features'
import { Films } from './pages/Films'
import { Home } from './pages/Home'
import { Install } from './pages/Install'
import { usePage, type Page } from './router'

const PAGES: Record<Page, { title: string; view: () => React.JSX.Element }> = {
  home: { title: 'EPM2Mod: firmware for the Olympus PEN E-PM2', view: Home },
  features: { title: 'Features · EPM2Mod', view: Features },
  films: { title: 'Film Simulations · EPM2Mod', view: Films },
  install: { title: 'Install · EPM2Mod', view: Install },
}

export default function App() {
  const page = usePage()
  const { title, view: View } = PAGES[page]

  // a new page starts at the top, or at its #anchor
  useEffect(() => {
    document.title = title
    const target = window.location.hash && document.getElementById(window.location.hash.slice(1))
    if (target) target.scrollIntoView()
    else window.scrollTo(0, 0)
  }, [page, title])

  return (
    <Layout page={page}>
      <View />
    </Layout>
  )
}
