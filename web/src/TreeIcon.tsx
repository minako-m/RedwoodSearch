// The redwood logo; the same drawing as public/favicon.svg.
export function TreeIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true" className={className}>
      <rect x="14" y="23" width="4" height="7" rx="1.5" fill="#8f623e" />
      <path d="M16 2 9 12h3.5L7 20h4l-5 6h20l-5-6h4l-5.5-8H23z" fill="#b0d4bd" />
      <path d="M16 2 9 12h3.5L7 20h4l-5 6h10z" fill="#d7eadd" />
    </svg>
  )
}
