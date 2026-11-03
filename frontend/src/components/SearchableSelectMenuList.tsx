import { MenuList, MenuListProps, Typography } from '@mui/material'
import { Children, CSSProperties, KeyboardEvent, ReactNode, forwardRef, isValidElement, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

function optionText(node: ReactNode): string {
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (!isValidElement<{ children?: ReactNode }>(node)) return ''
  return Children.toArray(node.props.children).map(optionText).join(' ')
}

function normalize(value: string): string {
  return value
    .normalize('NFKD')
    .replace(/\p{M}/gu, '')
    .replace(/\s+/g, ' ')
    .trim()
    .toLocaleLowerCase()
}

export const SearchableSelectMenuList = forwardRef<HTMLUListElement, MenuListProps>(function SearchableSelectMenuList(
  { children, ...menuListProps },
  forwardedRef,
) {
  const listRef = useRef<HTMLUListElement | null>(null)
  const inputRef = useRef<HTMLInputElement | null>(null)
  const [search, setSearch] = useState('')
  const [target, setTarget] = useState<{ field: HTMLElement, host: HTMLElement, style: CSSProperties } | null>(null)
  const query = normalize(search)
  const options = useMemo(() => Children.toArray(children), [children])
  const indexedOptions = useMemo(
    () => options.map(option => ({ option, label: normalize(optionText(option)) })),
    [options],
  )
  const filteredOptions = useMemo(
    () => query ? indexedOptions.filter(({ label }) => label.includes(query)).map(({ option }) => option) : options,
    [indexedOptions, options, query],
  )

  useLayoutEffect(() => {
    const list = listRef.current
    const field = list?.id
      ? document.querySelector<HTMLElement>(`[role="combobox"][aria-controls="${CSS.escape(list.id)}"]`)
      : null
    const host = list?.closest<HTMLElement>('.MuiModal-root') ?? list?.parentElement
    if (!field || !host) return

    const computed = window.getComputedStyle(field)
    const bounds = field.getBoundingClientRect()
    const paper = list?.parentElement
    const positionMenuBelowField = () => {
      if (!paper) return
      const currentBounds = field.getBoundingClientRect()
      const gap = 6
      const viewportPadding = 8
      const availableHeight = Math.max(48, window.innerHeight - currentBounds.bottom - gap - viewportPadding)
      paper.style.setProperty('top', `${currentBounds.bottom + gap}px`, 'important')
      paper.style.setProperty('bottom', 'auto', 'important')
      paper.style.setProperty('transform-origin', 'top left', 'important')
      paper.style.setProperty('max-height', `${Math.min(360, availableHeight)}px`, 'important')
    }
    const previousVisibility = field.style.visibility
    field.style.visibility = 'hidden'
    setTarget({
      field,
      host,
      style: {
        position: 'fixed', zIndex: 1400, boxSizing: 'border-box',
        top: bounds.top, left: bounds.left, width: bounds.width, height: bounds.height,
        padding: computed.padding, border: 0, outline: 0, background: 'transparent', color: computed.color,
        font: computed.font, letterSpacing: computed.letterSpacing, cursor: 'text',
      },
    })
    positionMenuBelowField()
    const positionFrame = window.requestAnimationFrame(positionMenuBelowField)
    window.addEventListener('resize', positionMenuBelowField)
    window.addEventListener('scroll', positionMenuBelowField, true)
    return () => {
      window.cancelAnimationFrame(positionFrame)
      window.removeEventListener('resize', positionMenuBelowField)
      window.removeEventListener('scroll', positionMenuBelowField, true)
      field.style.visibility = previousVisibility
    }
  }, [])

  useLayoutEffect(() => {
    if (target) inputRef.current?.focus()
  }, [target])

  const setRefs = (node: HTMLUListElement | null) => {
    listRef.current = node
    if (typeof forwardedRef === 'function') forwardedRef(node)
    else if (forwardedRef) forwardedRef.current = node
  }

  const handleInputKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key.length === 1 || event.key === 'Backspace' || event.key === 'Delete') event.stopPropagation()
  }

  return <>
    {target && createPortal(
      <input
        ref={inputRef}
        type="text"
        role="searchbox"
        aria-label="Search dropdown options"
        autoComplete="off"
        value={search}
        placeholder="Type to search…"
        onChange={event => setSearch(event.target.value)}
        onKeyDown={handleInputKeyDown}
        style={target.style}
      />,
      target.host,
    )}
    <MenuList {...menuListProps} ref={setRefs}>
      {filteredOptions.length > 0
        ? filteredOptions
        : <Typography component="li" role="status" variant="body2" color="text.secondary" sx={{ px: 2, py: 1.5, listStyle: 'none' }}>No matching options</Typography>}
    </MenuList>
  </>
})
