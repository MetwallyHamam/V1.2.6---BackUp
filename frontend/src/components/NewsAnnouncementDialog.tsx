import { Campaign, ChatBubbleOutline, CheckCircle, Close, Favorite, FavoriteBorder, Newspaper, Send, VisibilityOff } from '@mui/icons-material'
import { Avatar, Box, Button, Chip, Dialog, DialogActions, DialogContent, Divider, LinearProgress, Paper, Stack, TextField, Typography } from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'

type NewsPost = {
  id: number
  template: string
  title: string
  summary: string
  body: string
  video_url?: string
  is_featured: boolean
  requires_confirmation: boolean
  image_url?: string
  confirmed: boolean
  liked: boolean
  like_count: number
  comment_count: number
  mentions: Array<{ id: number; name: string }>
  poll_options: Array<{ id: number; label: string; votes: number }>
  poll_vote_option_id?: number
}
type NewsComment = { id: number; author_user_id: number; author_name: string; body: string; created_at: string }
type MentionCandidate = { id: number; full_name: string; is_active: boolean }

const colors: Record<string, string> = { NEWCOMER: '#7c3aed', ANNOUNCEMENT: '#2563eb', UPDATE: '#00897b', EVENT: '#d97706', MAINTENANCE: '#dc2626', GENERAL: '#475569' }

function embedUrl(value?: string) {
  if (!value) return ''
  try {
    const url = new URL(value)
    if (url.hostname === 'youtu.be') return `https://www.youtube.com/embed/${url.pathname.slice(1)}`
    if (url.hostname.endsWith('youtube.com')) return `https://www.youtube.com/embed/${url.searchParams.get('v') ?? ''}`
    const match = url.pathname.match(/\/(\d+)/)
    if (url.hostname.endsWith('vimeo.com') && match) return `https://player.vimeo.com/video/${match[1]}`
  } catch { return '' }
  return ''
}

export function NewsAnnouncementDialog() {
  const { t } = useTranslation()
  const { hasPermission, user } = useAuth()
  const queryClient = useQueryClient()
  const [closedIds, setClosedIds] = useState<number[]>([])
  const [imageUrl, setImageUrl] = useState('')
  const [comment, setComment] = useState('')
  const [commentMentionIds, setCommentMentionIds] = useState<number[]>([])
  const news = useQuery({
    queryKey: ['news', 'feed'],
    queryFn: async () => (await api.get<NewsPost[]>('/news')).data,
    enabled: Boolean(user && hasPermission('news.view')),
    staleTime: 30_000,
  })
  const post = useMemo(() => news.data?.find(item => !closedIds.includes(item.id)), [closedIds, news.data])
  const action = useMutation({
    mutationFn: async ({ id, value }: { id: number; value: 'VIEW' | 'CONFIRM' | 'DISMISS' }) => (await api.post(`/news/${id}/action`, null, { params: { action: value } })).data,
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: ['news'] }),
  })
  const comments = useQuery({ queryKey: ['news-comments', post?.id], queryFn: async () => (await api.get<NewsComment[]>(`/news/${post!.id}/comments`)).data, enabled: Boolean(post) })
  const mentionCandidates = useQuery({ queryKey: ['news-mention-users'], queryFn: async () => (await api.get<MentionCandidate[]>('/news/mention-candidates')).data, enabled: Boolean(post && comment.includes('@')) })
  const like = useMutation({ mutationFn: async () => (await api.post<NewsPost>(`/news/${post!.id}/like`)).data, onSuccess: async () => queryClient.invalidateQueries({ queryKey: ['news'] }) })
  const vote = useMutation({ mutationFn: async (optionId: number) => (await api.post<NewsPost>(`/news/${post!.id}/poll/${optionId}`)).data, onSuccess: async () => queryClient.invalidateQueries({ queryKey: ['news'] }) })
  const addComment = useMutation({ mutationFn: async () => (await api.post(`/news/${post!.id}/comments`, { body: comment.trim(), mention_user_ids: commentMentionIds })).data, onSuccess: async () => { setComment(''); setCommentMentionIds([]); await queryClient.invalidateQueries({ queryKey: ['news-comments', post?.id] }); await queryClient.invalidateQueries({ queryKey: ['news'] }) } })

  useEffect(() => {
    if (!post) return
    action.mutate({ id: post.id, value: 'VIEW' })
    // A new post identity is the only event that should record a view.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [post?.id])

  useEffect(() => {
    let objectUrl = ''
    let active = true
    setImageUrl('')
    if (post?.image_url) api.get(post.image_url, { responseType: 'blob' }).then(response => {
      if (active) { objectUrl = URL.createObjectURL(response.data); setImageUrl(objectUrl) }
    }).catch(() => undefined)
    return () => { active = false; if (objectUrl) URL.revokeObjectURL(objectUrl) }
  }, [post?.id, post?.image_url])

  if (!post) return null
  const close = () => setClosedIds(current => [...current, post.id])
  const respond = async (value: 'CONFIRM' | 'DISMISS') => {
    await action.mutateAsync({ id: post.id, value })
    close()
  }
  const video = embedUrl(post.video_url)
  const accent = colors[post.template] ?? colors.GENERAL
  const totalVotes = post.poll_options.reduce((sum, option) => sum + option.votes, 0)
  const mentionMatch = comment.match(/(?:^|\s)@([^@]*)$/)
  const mentionQuery = mentionMatch?.[1].trim().toLocaleLowerCase() ?? ''
  const mentionOptions = mentionMatch ? (mentionCandidates.data ?? []).filter(candidate => candidate.is_active && candidate.full_name.toLocaleLowerCase().includes(mentionQuery)).slice(0, 8) : []
  const selectMention = (candidate: MentionCandidate) => {
    const atIndex = comment.lastIndexOf('@')
    setComment(`${comment.slice(0, atIndex)}@${candidate.full_name} `)
    setCommentMentionIds(current => current.includes(candidate.id) ? current : [...current, candidate.id])
  }

  return <Dialog open fullWidth maxWidth="md" onClose={close} PaperProps={{ sx: { borderRadius: 4, overflow: 'hidden' } }}>
    <Box sx={{ position: 'relative', minHeight: imageUrl ? 260 : 150, display: 'grid', placeItems: 'center', color: 'white', background: imageUrl ? `linear-gradient(180deg,transparent 35%,rgba(15,23,42,.88)),url(${imageUrl}) center/cover` : `linear-gradient(135deg,${accent},#0f172a)` }}>
      {!imageUrl && <Campaign sx={{ fontSize: 72, opacity: .7 }} />}
      <Button aria-label={t('common.close')} onClick={close} sx={{ position: 'absolute', top: 12, insetInlineEnd: 12, minWidth: 40, width: 40, height: 40, borderRadius: '50%', color: 'white', bgcolor: 'rgba(15,23,42,.48)', '&:hover': { bgcolor: 'rgba(15,23,42,.72)' } }}><Close /></Button>
      <Chip icon={<Newspaper />} label={t(`news.templates.${post.template}`)} sx={{ position: 'absolute', bottom: 16, insetInlineStart: 20, color: 'white', bgcolor: accent, '& .MuiChip-icon': { color: 'white' } }} />
    </Box>
    <DialogContent sx={{ px: { xs: 2.5, sm: 4 }, py: 3 }}>
      <Typography variant="overline" color="primary" fontWeight={800}>{t('news.popupEyebrow')}</Typography>
      <Typography variant="h4" fontWeight={900} sx={{ mt: .25 }}>{post.title}</Typography>
      <Typography variant="h6" color="text.secondary" fontWeight={500} sx={{ mt: 1 }}>{post.summary}</Typography>
      {video && <Box component="iframe" src={video} title={post.title} allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" sx={{ border: 0, width: '100%', aspectRatio: '16/9', mt: 2.5, borderRadius: 2 }} />}
      <Typography sx={{ whiteSpace: 'pre-wrap', mt: 2.5, lineHeight: 1.8 }}>{post.body}</Typography>
      {post.mentions.length > 0 && <Stack direction="row" gap={.75} flexWrap="wrap" mt={2}>{post.mentions.map(person => <Chip key={person.id} size="small" label={`@${person.name}`} />)}</Stack>}
      {post.poll_options.length > 0 && <Box sx={{ mt: 3, p: 2, borderRadius: 2, bgcolor: 'action.hover' }}><Typography fontWeight={800} mb={1}>{t('news.poll')}</Typography><Stack spacing={1}>{post.poll_options.map(option => { const percent = totalVotes ? Math.round(option.votes * 100 / totalVotes) : 0; return <Button key={option.id} variant={post.poll_vote_option_id === option.id ? 'contained' : 'outlined'} disabled={vote.isPending} onClick={() => vote.mutate(option.id)} sx={{ display: 'block', textAlign: 'start', py: 1 }}><Stack direction="row" justifyContent="space-between"><span>{option.label}</span><span>{percent}%</span></Stack><LinearProgress variant="determinate" value={percent} color="inherit" sx={{ mt: .75, height: 4, borderRadius: 2 }} /></Button> })}</Stack><Typography variant="caption" color="text.secondary">{t('news.votes', { count: totalVotes })}</Typography></Box>}
      <Divider sx={{ my: 2.5 }} />
      <Stack direction="row" gap={1}><Button startIcon={post.liked ? <Favorite /> : <FavoriteBorder />} color={post.liked ? 'error' : 'inherit'} onClick={() => like.mutate()}>{post.like_count} {t('news.likes')}</Button><Button startIcon={<ChatBubbleOutline />} color="inherit">{comments.data?.length ?? post.comment_count} {t('news.comments')}</Button></Stack>
      <Stack spacing={1.25} mt={2}>{comments.data?.map(item => <Stack key={item.id} direction="row" gap={1}><Avatar sx={{ width: 32, height: 32 }}>{item.author_name[0]}</Avatar><Box sx={{ bgcolor: 'action.hover', borderRadius: 2, px: 1.5, py: .75, flex: 1 }}><Typography variant="caption" fontWeight={800}>{item.author_name}</Typography><Typography>{item.body}</Typography></Box></Stack>)}</Stack>
      <Box sx={{ mt: 2, position: 'relative' }}><Stack direction="row" gap={1}><TextField fullWidth size="small" value={comment} onChange={event => setComment(event.target.value)} label={t('news.writeComment')} helperText="Type @ to mention a person" inputProps={{ maxLength: 2000 }} /><Button variant="contained" aria-label={t('news.postComment')} disabled={!comment.trim() || addComment.isPending} onClick={() => addComment.mutate()}><Send /></Button></Stack>{mentionMatch && mentionOptions.length > 0 && <Paper elevation={8} sx={{ position: 'absolute', zIndex: 2, left: 0, right: 56, bottom: '100%', mb: .5, maxHeight: 240, overflowY: 'auto' }}>{mentionOptions.map(candidate => <Button key={candidate.id} fullWidth sx={{ justifyContent: 'flex-start', px: 2, py: 1 }} onClick={() => selectMention(candidate)}>@{candidate.full_name}</Button>)}</Paper>}</Box>
    </DialogContent>
    <DialogActions sx={{ px: { xs: 2.5, sm: 4 }, pb: 3, gap: 1, flexWrap: 'wrap' }}>
      <Button startIcon={<VisibilityOff />} disabled={action.isPending} onClick={() => void respond('DISMISS')}>{t('news.dontShow')}</Button>
      <Button sx={{ ms: 'auto' }} variant={post.requires_confirmation && !post.confirmed ? 'contained' : 'outlined'} startIcon={<CheckCircle />} disabled={action.isPending} onClick={() => post.requires_confirmation && !post.confirmed ? void respond('CONFIRM') : close()}>{post.requires_confirmation && !post.confirmed ? t('news.confirm') : t('news.gotIt')}</Button>
    </DialogActions>
  </Dialog>
}
