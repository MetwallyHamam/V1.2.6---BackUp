import { ArrowBack } from '@mui/icons-material'
import { Button, Paper, Stack, Typography } from '@mui/material'
import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

type VisitedPage = { label: string; path: string }

const recentPagesKey = 'support-hub-recent-pages-v1'
const maximumRecentPages = 6

function readRecentPages(): VisitedPage[] {
  try {
    const value = JSON.parse(window.sessionStorage.getItem(recentPagesKey) ?? '[]')
    if (!Array.isArray(value)) return []
    return value.filter((page): page is VisitedPage => Boolean(page?.label && page?.path))
  } catch {
    return []
  }
}

export function PageContextHeader({ homeLabel, title }: { homeLabel: string; title: string }) {
  const navigate = useNavigate()
  const location = useLocation()
  const currentPath = `${location.pathname}${location.search}`
  const [recentPages, setRecentPages] = useState<VisitedPage[]>(readRecentPages)

  useEffect(() => {
    setRecentPages(current => {
      const withoutCurrent = current.filter(
        page => page.path !== currentPath && page.label !== title,
      )
      const next = [...withoutCurrent, { label: title, path: currentPath }].slice(-maximumRecentPages)
      window.sessionStorage.setItem(recentPagesKey, JSON.stringify(next))
      return next
    })
  }, [currentPath, title])

  const visitedPages = recentPages
    .filter(page => page.path !== currentPath && page.label !== title)
    .filter(
      (page, index, pages) =>
        pages.findIndex(candidate => candidate.label === page.label) === index,
    )
    .slice(-5)
    .reverse()
  const previousPage = visitedPages[0] ?? null
  const previousLabel = previousPage?.label ?? homeLabel
  const goBack = () => {
    if (previousPage) navigate(previousPage.path)
    else if (window.history.length > 1) navigate(-1)
    else navigate(location.pathname.startsWith('/portal') ? '/portal' : '/home')
  }

  return <Paper component="header" variant="outlined" sx={{ px: { xs: 1, sm: 1.5 }, py: .75, mb: 1 }}>
    <Stack direction="row" alignItems="center" gap={.75} minHeight={36}>
      <Button
        size="small"
        color="inherit"
        startIcon={<ArrowBack />}
        onClick={goBack}
        sx={{ minWidth: 0, textTransform: 'none', fontWeight: 700 }}
      >
        {previousLabel}
      </Button>
      <Typography color="text.secondary" aria-hidden>/</Typography>
      <Typography color="text.primary" fontWeight={700} noWrap>{title}</Typography>
      {visitedPages.length > 0 && <Stack
        component="nav"
        aria-label="Recently visited pages"
        direction="row"
        gap={.25}
        alignItems="center"
        sx={{ marginInlineStart: 'auto', overflowX: 'auto', minWidth: 0 }}
      >
        {visitedPages.map(page => <Button
          key={page.path}
          size="small"
          color="inherit"
          onClick={() => navigate(page.path)}
          sx={{ flexShrink: 0, minWidth: 0, px: 1, textTransform: 'none', color: 'text.secondary' }}
        >
          {page.label}
        </Button>)}
      </Stack>}
    </Stack>
  </Paper>
}
