import { Autocomplete, AutocompleteProps, Box, Button, Paper, useMediaQuery, useTheme } from '@mui/material'
import { ComponentType, HTMLAttributes, useEffect, useRef, useState } from 'react'

type Props<T> = Omit<AutocompleteProps<T, true, false, false>, 'multiple'>

type CloseWatcherInstance = { close(): void; destroy(): void; onclose: (() => void) | null }
type CloseWatcherConstructor = new () => CloseWatcherInstance

export function MobileMultiAutocomplete<T>(props: Props<T>) {
  const theme = useTheme()
  const mobile = useMediaQuery(theme.breakpoints.down('sm'))
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState<T[]>(props.value ?? [])
  const snapshot = useRef<T[]>(props.value ?? [])

  const cancel = () => {
    setDraft(snapshot.current)
    setOpen(false)
  }
  const done = () => {
    props.onChange?.({ type: 'change' } as never, [...draft], 'selectOption', undefined)
    setOpen(false)
  }

  useEffect(() => {
    if (!open || !mobile) return
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const CloseWatcher = (window as Window & { CloseWatcher?: CloseWatcherConstructor }).CloseWatcher
    const watcher = CloseWatcher ? new CloseWatcher() : null
    if (watcher) watcher.onclose = cancel
    return () => {
      watcher?.destroy()
      document.body.style.overflow = previousOverflow
    }
  }, [open, mobile])

  const MobilePaper: ComponentType<HTMLAttributes<HTMLElement>> = ({ children, ...paperProps }) => (
    <Paper {...paperProps} elevation={8} sx={{ display: 'flex', flexDirection: 'column', maxHeight: 'min(70dvh, 560px)' }}>
      <Box sx={{ overflowY: 'auto', flex: 1 }}>{children}</Box>
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, p: 1, borderTop: 1, borderColor: 'divider' }}>
        <Button onMouseDown={event => event.preventDefault()} onClick={cancel}>Cancel</Button>
        <Button variant="contained" onMouseDown={event => event.preventDefault()} onClick={done}>Done</Button>
      </Box>
    </Paper>
  )

  return <Autocomplete<T, true, false, false>
    {...props}
    multiple
    disableCloseOnSelect={mobile || props.disableCloseOnSelect}
    open={open}
    value={mobile && open ? draft : (props.value ?? [])}
    onOpen={() => {
      snapshot.current = [...(props.value ?? [])]
      setDraft([...(props.value ?? [])])
      setOpen(true)
      props.onOpen?.({ type: 'open' } as never)
    }}
    onClose={(event, reason) => {
      if (!mobile || reason === 'blur') setOpen(false)
      else if (reason === 'escape') cancel()
      props.onClose?.(event, reason)
    }}
    onChange={(event, value, reason, details) => {
      if (mobile && open) setDraft(value)
      else props.onChange?.(event, value, reason, details)
    }}
    slots={mobile ? { ...props.slots, paper: MobilePaper } : props.slots}
  />
}
