export function scoreBadgeClass(score?: number | null): string {
  if (score == null) return 'bg-slate-500/10 text-slate-700 ring-1 ring-slate-300/70'
  if (score >= 0.9) return 'bg-emerald-500/14 text-emerald-950 ring-1 ring-emerald-400/25'
  if (score >= 0.75) return 'bg-sky-500/14 text-sky-950 ring-1 ring-sky-400/25'
  if (score >= 0.6) return 'bg-amber-500/16 text-amber-950 ring-1 ring-amber-400/25'
  return 'bg-rose-500/14 text-rose-950 ring-1 ring-rose-400/25'
}

export function scoreSurfaceClass(score?: number | null): string {
  if (score == null) return 'border-white/70 bg-white/72'
  if (score >= 0.9) return 'border-emerald-200/70 bg-emerald-50/45'
  if (score >= 0.75) return 'border-sky-200/70 bg-sky-50/45'
  if (score >= 0.6) return 'border-amber-200/70 bg-amber-50/45'
  return 'border-rose-200/70 bg-rose-50/45'
}

export function formatPercent(score?: number | null): string {
  if (score == null || Number.isNaN(score)) return 'N/A'
  return `${Math.round(score * 100)}%`
}

export function formatMoney(value?: number | null): string {
  if (value == null || Number.isNaN(value)) return 'N/A'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value)
}

export function formatDateTime(value?: string | null): string {
  if (!value) return 'N/A'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleString()
}

export function formatDuration(hours?: number | null): string {
  if (hours == null || Number.isNaN(hours)) return 'N/A'
  const totalMinutes = Math.round(hours * 60)
  const wholeHours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60

  if (wholeHours <= 0) return `${minutes} min`
  if (minutes === 0) return `${wholeHours} hr`
  return `${wholeHours} hr ${minutes} min`
}
