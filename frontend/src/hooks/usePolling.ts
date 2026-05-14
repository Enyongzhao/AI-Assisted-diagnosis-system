// implementation_plan.md Step 3.5 — Polling hook
// Polls a fetch function every `interval` ms until isDone returns true.
// Uses a ref-based timer to avoid stale-closure issues.
import { useState, useEffect, useRef, useCallback } from 'react'

interface UsePollingResult<T> {
  data: T | null
  loading: boolean
  error: string | null
  // Call to restart polling manually (e.g. after submitting opinion)
  restart: () => void
}

export function usePolling<T>(
  fetchFn: () => Promise<T>,
  isDone: (data: T) => boolean,
  interval = 3000
): UsePollingResult<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Refs survive re-renders without triggering effect restarts
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mountedRef = useRef(true)
  // Wrap fetchFn/isDone in refs so the stable `poll` closure always sees latest values
  const fetchRef = useRef(fetchFn)
  const doneRef = useRef(isDone)
  fetchRef.current = fetchFn
  doneRef.current = isDone

  const clearTimer = () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }

  const poll = useCallback(async () => {
    if (!mountedRef.current) return
    try {
      const result = await fetchRef.current()
      if (!mountedRef.current) return
      setData(result)
      setError(null)
      setLoading(false)
      if (!doneRef.current(result)) {
        timerRef.current = setTimeout(poll, interval)
      }
    } catch (err) {
      if (!mountedRef.current) return
      const msg = err instanceof Error ? err.message : 'Polling failed'
      setError(msg)
      setLoading(false)
    }
  }, [interval])

  // restart clears any pending timer then starts a fresh poll cycle
  const restart = useCallback(() => {
    clearTimer()
    setLoading(true)
    setError(null)
    poll()
  }, [poll])

  useEffect(() => {
    mountedRef.current = true
    poll()
    return () => {
      mountedRef.current = false
      clearTimer()
    }
  }, [poll])

  return { data, loading, error, restart }
}
