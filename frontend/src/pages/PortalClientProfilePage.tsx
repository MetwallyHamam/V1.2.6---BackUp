import { Business, Email, LocationOn, Person, Phone } from '@mui/icons-material'
import { Alert, Box, Chip, CircularProgress, FormControl, Grid, InputLabel, MenuItem, Paper, Select, Stack, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api/client'
import { ClientLifecycleOverview, type ClientLifecycle } from '../components/ClientLifecycleOverview'

type ClientSummary = { id:number; code:string; name:string }
type Profile = {
  clients: ClientSummary[]
  client: ClientSummary & { status:string; timezone:string; country?:string; zone?:string; phone_number?:string; email?:string; address?:string; support_started_at?:string; contract_service_status:string }
  branches: Array<{id:number;code:string;name:string;country?:string;zone?:string;phone_number?:string;email?:string;address?:string;support_hours?:string;timezone?:string}>
  contacts: Array<{id:number;full_name:string;email?:string;phone_number?:string;job_title?:string;contact_role?:string;is_primary:boolean;is_escalation_contact:boolean}>
  lifecycle: ClientLifecycle
}

const Detail = ({ icon, value }:{icon:React.ReactNode;value?:string}) => value ? <Stack direction="row" spacing={1} alignItems="center">{icon}<Typography>{value}</Typography></Stack> : null

export function PortalClientProfilePage() {
  const [clientId,setClientId]=useState<number | ''>('')
  const query=useQuery({queryKey:['portal-client-profile',clientId],queryFn:async()=>(await api.get<Profile>('/portal/client-profile',{params:clientId ? {client_id:clientId}:undefined})).data})
  const data=query.data
  return <Stack spacing={3}>
    <Paper sx={{p:3,background:'linear-gradient(120deg, #145da0, #6a1b9a)',color:'white'}}><Typography variant="h3">Client profile</Typography><Typography sx={{mt:1}}>Your organization details and support contacts.</Typography></Paper>
    {query.isLoading&&<CircularProgress/>}{query.isError&&<Alert severity="error">The client profile could not be loaded.</Alert>}
    {data&&<>
      {data.clients.length>1&&<FormControl sx={{maxWidth:420}}><InputLabel>Client</InputLabel><Select label="Client" value={clientId||data.client.id} onChange={event=>setClientId(Number(event.target.value))}>{data.clients.map(item=><MenuItem key={item.id} value={item.id}>{item.name} ({item.code})</MenuItem>)}</Select></FormControl>}
      <Paper variant="outlined" sx={{p:3}}><Stack direction={{xs:'column',md:'row'}} justifyContent="space-between" gap={2}><Box><Typography variant="h4">{data.client.name}</Typography><Typography color="text.secondary">{data.client.code}</Typography></Box><Stack direction="row" gap={1} flexWrap="wrap"><Chip color="success" label={data.client.status}/><Chip variant="outlined" label={data.client.contract_service_status.replaceAll('_',' ')}/></Stack></Stack><Grid container spacing={2} mt={1}><Grid size={{xs:12,md:6}}><Stack spacing={1}><Detail icon={<Email color="action"/>} value={data.client.email}/><Detail icon={<Phone color="action"/>} value={data.client.phone_number}/><Detail icon={<LocationOn color="action"/>} value={[data.client.address,data.client.zone,data.client.country].filter(Boolean).join(', ')}/></Stack></Grid><Grid size={{xs:12,md:6}}><Typography><b>Timezone:</b> {data.client.timezone}</Typography>{data.client.support_started_at&&<Typography><b>Support since:</b> {new Date(data.client.support_started_at).toLocaleDateString()}</Typography>}</Grid></Grid></Paper>
      <ClientLifecycleOverview lifecycle={data.lifecycle}/>
      <Box><Typography variant="h5" mb={1}>Branches</Typography><Grid container spacing={2}>{data.branches.map(branch=><Grid key={branch.id} size={{xs:12,md:6}}><Paper variant="outlined" sx={{p:2,height:'100%'}}><Typography variant="h6"><Business sx={{verticalAlign:'middle',mr:1}}/>{branch.name}</Typography><Typography color="text.secondary" mb={1}>{branch.code}</Typography><Stack spacing={.75}><Detail icon={<Email fontSize="small"/>} value={branch.email}/><Detail icon={<Phone fontSize="small"/>} value={branch.phone_number}/><Detail icon={<LocationOn fontSize="small"/>} value={[branch.address,branch.zone,branch.country].filter(Boolean).join(', ')}/>{branch.support_hours&&<Typography variant="body2"><b>Support hours:</b> {branch.support_hours}</Typography>}</Stack></Paper></Grid>)}{!data.branches.length&&<Typography color="text.secondary">No active branches.</Typography>}</Grid></Box>
      <Box><Typography variant="h5" mb={1}>Contacts</Typography><Grid container spacing={2}>{data.contacts.map(contact=><Grid key={contact.id} size={{xs:12,sm:6,lg:4}}><Paper variant="outlined" sx={{p:2,height:'100%'}}><Typography variant="h6"><Person sx={{verticalAlign:'middle',mr:1}}/>{contact.full_name}</Typography><Typography color="text.secondary">{contact.job_title||contact.contact_role}</Typography><Stack direction="row" gap={1} my={1}>{contact.is_primary&&<Chip size="small" color="primary" label="Primary"/>}{contact.is_escalation_contact&&<Chip size="small" color="warning" label="Escalation"/>}</Stack><Detail icon={<Email fontSize="small"/>} value={contact.email}/><Detail icon={<Phone fontSize="small"/>} value={contact.phone_number}/></Paper></Grid>)}{!data.contacts.length&&<Typography color="text.secondary">No active contacts.</Typography>}</Grid></Box>
    </>}
  </Stack>
}
