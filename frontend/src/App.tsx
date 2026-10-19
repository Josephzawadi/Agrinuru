import { useEffect, useState } from 'react'
import './App.css'

type ApiStatus = 'checking' | 'online' | 'offline'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>('checking')

  useEffect(() => {
    const controller = new AbortController()
    fetch(`${apiBaseUrl}/api/health/`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error('Health check failed')
        return response.json()
      })
      .then(() => setApiStatus('online'))
      .catch(() => {
        if (!controller.signal.aborted) setApiStatus('offline')
      })

    return () => controller.abort()
  }, [])

  const apiStatusLabel = {
    checking: 'Connecting to the platform',
    online: 'Platform services are running',
    offline: 'Platform API is not reachable',
  }[apiStatus]

  return (
    <div className="site-shell" id="top">
      <header className="site-header">
        <a className="brand" href="#top" aria-label="AgriNuru home">
          <span className="brand-mark" aria-hidden="true">A</span>
          <span>AgriNuru</span>
        </a>
        <nav className="header-nav" aria-label="Main navigation">
          <a href="#approach">Our approach</a>
          <a className="header-cta" href="#foundation">Platform overview <span aria-hidden="true">↗</span></a>
        </nav>
      </header>

      <main>
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-copy">
            <p className="eyebrow"><span /> Decisions for every season</p>
            <h1 id="hero-title">A clearer view of <em>what comes next.</em></h1>
            <p className="hero-description">
              Bring crop plans, weather conditions, harvest records, and market
              prices into one place. Make the next farm decision with more of
              the picture in view.
            </p>
            <div className="hero-actions">
              <a className="button-primary" href="#approach">Explore the approach <span aria-hidden="true">→</span></a>
              <a className="text-link" href="#foundation">See what we are building</a>
            </div>
            <div className={`service-status status-${apiStatus}`} role="status" aria-live="polite">
              <span className="status-light" aria-hidden="true" />
              {apiStatusLabel}
            </div>
          </div>

          <figure className="hero-visual">
            <img
              src="https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=1800&q=85"
              alt="Green fields and farmland stretching toward the horizon"
            />
            <figcaption>
              <span>THE WHOLE SEASON, IN VIEW</span>
              <span>PRODUCTION · WEATHER · MARKET</span>
            </figcaption>
            <div className="visual-index" aria-hidden="true">01 <span>/</span> 03</div>
          </figure>
        </section>

        <section className="approach-band" id="approach" aria-label="AgriNuru approach">
          <p>Good decisions begin with connected information.</p>
          <div className="approach-tags">
            <span>Plan with context</span>
            <span>Read the market</span>
            <span>Learn from each harvest</span>
          </div>
        </section>

        <section className="foundation" id="foundation" aria-labelledby="foundation-title">
          <div className="foundation-heading">
            <p className="eyebrow"><span /> A season, connected</p>
            <h2 id="foundation-title">From the first plan to the final sale.</h2>
          </div>
          <div className="foundation-list">
            <article className="foundation-row">
              <span className="row-number">01</span>
              <h3>Plan the season</h3>
              <p>Keep farm details, crop plans, and growing conditions together.</p>
              <span className="row-symbol" aria-hidden="true">↗</span>
            </article>
            <article className="foundation-row">
              <span className="row-number">02</span>
              <h3>Understand the market</h3>
              <p>Compare dated crop prices and make the source of each figure clear.</p>
              <span className="row-symbol" aria-hidden="true">↗</span>
            </article>
            <article className="foundation-row">
              <span className="row-number">03</span>
              <h3>Learn from results</h3>
              <p>Record harvests and use past seasons to inform the next decision.</p>
              <span className="row-symbol" aria-hidden="true">↗</span>
            </article>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <a className="brand footer-brand" href="#top"><span className="brand-mark" aria-hidden="true">A</span><span>AgriNuru</span></a>
        <p>A production and market decision support project.</p>
        <span>Built for better-informed growing.</span>
      </footer>
    </div>
  )
}

export default App
