import { ArrowBack } from '@mui/icons-material'
import { Breadcrumbs, Button, Paper, Stack, Tab, Tabs, Typography } from '@mui/material'
import { useEffect, useState } from 'react'
import { Link as RouterLink, useLocation, useNavigate } from 'react-router-dom'

type ContextLink = { label: string; path: string; selected: boolean }
type OpenedPage = { label: string; path: string }

const openedPagesKey = 'support-hub-opened-page-tabs-v2'
const maximumOpenedPages = 8

function savedOpenedPages(): OpenedPage[] {
  try {
    const value = JSON.parse(window.sessionStorage.getItem(openedPagesKey) ?? '[]')
    if (!Array.isArray(value)) return []
    const unique = new Map<string, OpenedPage>()
    value
      .filter((item): item is OpenedPage => Boolean(item?.label && item?.path))
      .forEach(item => unique.set(item.label.trim().toLocaleLowerCase(), item))
    return [...unique.values()].slice(-maximumOpenedPages)
  } catch {
    return []
  }
}

export function PageContextHeader({ area, homeLabel, title, links }: { area: string; homeLabel: string; title: string; links: ContextLink[] }) {
  const navigate = useNavigate()
  const location = useLocation()
  const currentPath = `${location.pathname}${location.search}`
  const [openedPages, setOpenedPages] = useState<OpenedPage[]>(savedOpenedPages)
  const back = () => window.history.length > 1 ? navigate(-1) : navigate(location.pathname.startsWith('/portal') ? '/portal' : '/home')
  useEffect(() => {
    setOpenedPages(current => {
      const labelKey = title.trim().toLocaleLowerCase()
      const homeKey = homeLabel.trim().toLocaleLowerCase()
      const unique = new Map<string, OpenedPage>()
      current.forEach(item => {
        const itemKey = item.label.trim().toLocaleLowerCase()
        if (itemKey !== homeKey) unique.set(itemKey, item)
      })
      if (labelKey !== homeKey) unique.set(labelKey, { label: title, path: currentPath })
      const next = [...unique.values()].slice(-maximumOpenedPages)
      window.sessionStorage.setItem(openedPagesKey, JSON.stringify(next))
      return next
    })
  }, [currentPath, homeLabel, title])
  const visibleOpenedPages = [...new Map(
    openedPages
      .filter(page => page.label.trim().toLocaleLowerCase() !== homeLabel.trim().toLocaleLowerCase())
      .map(page => [page.label.trim().toLocaleLowerCase(), page] as const),
  ).values()].slice(-maximumOpenedPages)
  return <Paper component="header" variant="outlined" sx={{ px: { xs: 1, sm: 1.5 }, py: .75, mb: 1 }}>
    <Stack direction="row" alignItems="center" gap={1}>
      <Button size="small" color="inherit" startIcon={<ArrowBack />} onClick={back} sx={{ minWidth: 0 }}>{homeLabel}</Button>
      <Breadcrumbs aria-label="Breadcrumb" sx={{ flex: 1 }}>
      <Typography component={RouterLink} to="/" color="inherit" sx={{ textDecoration: 'none' }}>{homeLabel}</Typography>
      <Typography color="text.primary">{title}</Typography>
      </Breadcrumbs>
      <Typography variant="subtitle1" fontWeight={800} sx={{ display: { xs: 'none', md: 'block' } }}>{title}</Typography>
    </Stack>
    {visibleOpenedPages.length > 1 && <Tabs
      value={visibleOpenedPages.some(item => item.path === currentPath) ? currentPath : false}
      onChange={(_, path: string) => navigate(path)}
      variant="scrollable"
      scrollButtons="auto"
      allowScrollButtonsMobile
      aria-label="Previously opened pages"
      sx={{ mt: .5, minHeight: 34, borderTop: 1, borderColor: 'divider', '& .MuiTab-root': { minHeight: 34, py: .5, px: 1.5, textTransform: 'none' } }}
    >
      {visibleOpenedPages.map(page => <Tab key={page.label.trim().toLocaleLowerCase()} value={page.path} label={page.label} />)}
    </Tabs>}
    {links.length > 1 && <Stack component="nav" aria-label={`${area} navigation`} direction="row" gap={.5} mt={.5} sx={{ overflowX: 'auto' }}>
      {links.map(link => <Button key={link.path} component={RouterLink} to={link.path} size="small" variant={link.selected ? 'contained' : 'text'} sx={{ flexShrink: 0, textTransform: 'none' }}>{link.label}</Button>)}
    </Stack>}
  </Paper>
}
