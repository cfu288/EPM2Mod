/** The credit for the film looks: fitted to film simulations of spektrafilm (CC BY-SA 4.0) and Spectral Film LUT (MIT). */
export function FilmCredit() {
  return (
    <p className="text-muted text-xs">
      The film simulations are derived from{' '}
      <a className="hover:text-ink underline" href="https://github.com/andreavolpato/spektrafilm">
        spektrafilm
      </a>{' '}
      by Andrea Volpato (CC BY-SA 4.0) and from{' '}
      <a className="hover:text-ink underline" href="https://github.com/JanLohse/spectral_film_lut">
        Spectral Film LUT
      </a>{' '}
      by Jan Lohse (MIT).
    </p>
  )
}
