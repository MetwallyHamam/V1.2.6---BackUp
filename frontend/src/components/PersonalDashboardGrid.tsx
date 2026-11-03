import { AspectRatio, DragIndicator, Save } from '@mui/icons-material'
import { Box, Button, Grid, IconButton, Stack } from '@mui/material'
import { useEffect, useState, type ReactNode } from 'react'

export type DashboardTile = { code: string; width: number; content: ReactNode }
type Position = { order: number; width: number }

export function PersonalDashboardGrid({ tiles, storageKey }: { tiles: DashboardTile[]; storageKey: string }) {
  const [layout, setLayout] = useState<Record<string, Position>>({})
  const [dragged, setDragged] = useState<string | null>(null)
  const [dirty, setDirty] = useState(false)
  useEffect(() => {
    try { setLayout(JSON.parse(localStorage.getItem(storageKey) || '{}')) }
    catch { setLayout({}) }
    setDirty(false)
  }, [storageKey])
  const ordered = [...tiles].sort((a, b) =>
    (layout[a.code]?.order ?? tiles.indexOf(a)) - (layout[b.code]?.order ?? tiles.indexOf(b)))
  const width = (tile: DashboardTile) => layout[tile.code]?.width ?? tile.width
  function move(target: string) {
    if (!dragged || dragged === target) return
    const codes = ordered.map(tile => tile.code)
    const from = codes.indexOf(dragged), to = codes.indexOf(target)
    if (from < 0 || to < 0) return
    codes.splice(to, 0, codes.splice(from, 1)[0])
    setLayout(current => Object.fromEntries(codes.map((code, order) => [code, {
      order, width: current[code]?.width ?? tiles.find(tile => tile.code === code)!.width,
    }])))
    setDragged(null)
    setDirty(true)
  }
  function resize(tile: DashboardTile) {
    const sizes = [4, 6, 8, 12]
    const current = width(tile)
    const next = sizes[(Math.max(0, sizes.indexOf(current)) + 1) % sizes.length]
    setLayout(value => ({ ...value, [tile.code]: { order: value[tile.code]?.order ?? ordered.indexOf(tile), width: next } }))
    setDirty(true)
  }
  return <Stack spacing={1}>
    <Box textAlign="right"><Button size="small" startIcon={<Save />} disabled={!dirty} onClick={() => {
      localStorage.setItem(storageKey, JSON.stringify(layout))
      setDirty(false)
    }}>Save layout</Button></Box>
    <Grid container spacing={2}>{ordered.map(tile => <Grid key={tile.code} size={{ xs: 12, md: width(tile) }} onDragOver={event => event.preventDefault()} onDrop={() => move(tile.code)}>
      <Box sx={{ height: '100%', position: 'relative' }}>
        <Stack direction="row" sx={{ position: 'absolute', zIndex: 5, top: 8, insetInlineEnd: 8, bgcolor: 'background.paper', borderRadius: 1, boxShadow: 2 }}>
          <IconButton size="small" draggable onDragStart={event => { event.stopPropagation(); setDragged(tile.code) }} onDragEnd={() => setDragged(null)} aria-label={`Move ${tile.code}`} title="Drag to move"><DragIndicator fontSize="small" /></IconButton>
          <IconButton size="small" onClick={() => resize(tile)} aria-label={`Resize ${tile.code}`} title="Resize widget"><AspectRatio fontSize="small" /></IconButton>
        </Stack>
        {tile.content}
      </Box>
    </Grid>)}</Grid>
  </Stack>
}
