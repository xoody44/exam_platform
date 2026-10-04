export function formatDuration(seconds: number | null): string {
  if (seconds == null) return '—'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  return `${h}ч ${m}м ${s}с`
}

export function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  const withZone = /([+-]\d{2}:\d{2}|Z)$/.test(iso) ? iso : `${iso}Z`
  return new Date(withZone).toLocaleString('ru-RU')
}