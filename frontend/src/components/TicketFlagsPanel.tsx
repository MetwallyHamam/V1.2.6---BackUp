import { Add, Flag } from '@mui/icons-material'
import { Alert, Button, Chip, FormControl, InputLabel, MenuItem, Paper, Select, Stack, Typography } from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api, apiErrorMessage } from '../api/client'
import { useAuth } from '../auth/AuthContext'

type FlagMaster={id:number;name:string;color:string;pauses_sla:boolean}
type Assignment={id:number;flag_id:number;name:string;color:string;pauses_sla:boolean}
export function TicketFlagsPanel({ticketId}:{ticketId:number}){
 const {hasPermission}=useAuth(),cache=useQueryClient(),[flagId,setFlagId]=useState('')
 const canView=hasPermission('ticket.flag.view'),canApply=hasPermission('ticket.flag.apply'),canRemove=hasPermission('ticket.flag.remove')
 const flags=useQuery({queryKey:['ticket-flag-options'],enabled:canApply,queryFn:async()=>(await api.get<FlagMaster[]>('/ticket-flags')).data})
 const active=useQuery({queryKey:['ticket-flags',ticketId],enabled:canView,queryFn:async()=>(await api.get<Assignment[]>(`/ticket-flags/ticket/${ticketId}`)).data})
 const refresh=()=>cache.invalidateQueries({queryKey:['ticket-flags',ticketId]})
 const apply=useMutation({mutationFn:async()=>{const flag=flags.data?.find(row=>row.id===Number(flagId));const reason=window.prompt(flag?.pauses_sla?'Reason for pausing SLA':'Reason for applying flag');if(!reason||reason.trim().length<3)throw new Error('A reason of at least 3 characters is required.');return api.post(`/ticket-flags/ticket/${ticketId}`,{flag_id:Number(flagId),reason:reason.trim()})},onSuccess:async()=>{setFlagId('');await refresh()}})
 const remove=useMutation({mutationFn:async(row:Assignment)=>{const reason=window.prompt(row.pauses_sla?'Reason for removing flag and resuming SLA':'Reason for removing flag');if(!reason||reason.trim().length<3)throw new Error('A reason of at least 3 characters is required.');return api.post(`/ticket-flags/assignment/${row.id}/remove`,{reason:reason.trim()})},onSuccess:refresh})
 if(!canView)return null
 const available=(flags.data??[]).filter(flag=>!(active.data??[]).some(row=>row.flag_id===flag.id))
 return <Paper variant="outlined" sx={{p:1.5,mt:1.5,width:'100%',minWidth:0,boxSizing:'border-box'}}><Stack gap={1} minWidth={0}><Stack direction="row" gap={.75} alignItems="center"><Flag color="action"/><Typography fontWeight={850} sx={{whiteSpace:'nowrap'}}>Ticket flags</Typography></Stack><Stack direction="row" gap={.75} flexWrap="wrap" minWidth={0}>{active.data?.map(row=><Chip key={row.id} label={`${row.name}${row.pauses_sla?' · SLA paused':''}`} sx={{bgcolor:row.color,color:'#fff',maxWidth:'100%'}} onDelete={canRemove?()=>remove.mutate(row):undefined}/>)}</Stack>{canApply&&<Stack direction={{xs:'column',md:'row'}} gap={.75} minWidth={0}><FormControl size="small" fullWidth><InputLabel>Add flag</InputLabel><Select value={flagId} label="Add flag" onChange={e=>setFlagId(String(e.target.value))}>{available.map(row=><MenuItem key={row.id} value={row.id}>{row.name}{row.pauses_sla?' — pauses SLA':''}</MenuItem>)}</Select></FormControl><Button startIcon={<Add/>} disabled={!flagId||apply.isPending} onClick={()=>apply.mutate()} sx={{whiteSpace:'nowrap'}}>Add</Button></Stack>}</Stack>{active.data?.some(row=>row.pauses_sla)&&<Alert severity="warning" sx={{mt:1}}>Resolution SLA is paused. Remove this flag to resume it.</Alert>}{(apply.isError||remove.isError)&&<Alert severity="error" sx={{mt:1}}>{apiErrorMessage(apply.error??remove.error)}</Alert>}</Paper>
}
