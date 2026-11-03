import { ArrowBack, OpenInNew } from '@mui/icons-material'
import { Alert, Box, Button, Chip, CircularProgress, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'

type Evidence = { title:string; definition:string; total:number; unit:string; rows:Array<Record<string,unknown>> }
type Profile = { client:{name:string}; evidence:Record<string,Evidence> }

export function ClientEvidencePage(){
  const {t,i18n}=useTranslation();const locale=i18n.resolvedLanguage==='ar'?'ar-EG':'en-US'
  const {id}=useParams(),navigate=useNavigate(),[params]=useSearchParams()
  const metric=params.get('metric')??'',dateFrom=params.get('date_from')??'',dateTo=params.get('date_to')??''
  const query=useQuery({queryKey:['client-evidence',id,metric,dateFrom,dateTo],queryFn:async()=>(await api.get<Profile>('/reports/client-profile',{params:{client_id:id,date_from:dateFrom,date_to:dateTo}})).data,enabled:Boolean(id&&metric&&dateFrom&&dateTo)})
  if(query.isLoading)return <Box minHeight={300} display="grid" sx={{placeItems:'center'}}><CircularProgress/></Box>
  if(query.isError||!query.data)return <Alert severity="error">{t('clientEvidence.loadFailed')}</Alert>
  const evidence=query.data.evidence[metric]
  if(!evidence)return <Alert severity="warning">{t('clientEvidence.unavailable')}</Alert>
  const columns=evidence.rows.length?Object.keys(evidence.rows[0]).filter(key=>key!=='route'):[]
  const formatValue=(column:string,value:unknown)=>{
    if(value==null)return '—'
    if(typeof value==='number')return Intl.NumberFormat(locale,{maximumFractionDigits:2}).format(value)
    if(column==='source')return t(`clientEvidence.sources.${String(value)}`,{defaultValue:String(value)})
    if(column==='last_delivered'){const parsed=new Date(String(value));if(!Number.isNaN(parsed.getTime()))return parsed.toLocaleString(locale)}
    return String(value)
  }
  const date=(value:string)=>new Date(`${value}T00:00:00`).toLocaleDateString(locale)
  const title=t(`clientEvidence.metrics.${metric}.title`,{defaultValue:evidence.title})
  const definition=t(`clientEvidence.metrics.${metric}.definition`,{defaultValue:evidence.definition})
  const unit=t(`clientEvidence.metrics.${metric}.unit`,{defaultValue:evidence.unit})
  return <Stack spacing={2}><Paper sx={{p:3,background:'linear-gradient(120deg,#123b5d,#1677a6)',color:'white'}}><Button color="inherit" startIcon={<ArrowBack/>} onClick={()=>navigate(`/clients/${id}/profile`)}>{t('clientEvidence.profile')}</Button><Stack direction={{xs:'column',md:'row'}} gap={2} alignItems={{md:'center'}}><Box flex={1}><Typography variant="h4" fontWeight={900}>{title}</Typography><Typography sx={{opacity:.85}}>{query.data.client.name} · {t('clientEvidence.period',{from:date(dateFrom),to:date(dateTo)})}</Typography></Box><Chip sx={{bgcolor:'white',fontWeight:900}} color="primary" label={t('clientEvidence.total',{value:Intl.NumberFormat(locale,{maximumFractionDigits:2}).format(evidence.total),unit})}/></Stack></Paper><Alert severity="info">{definition}</Alert><Paper sx={{p:2,overflowX:'auto'}}>{!evidence.rows.length?<Alert severity="info">{t('clientEvidence.empty')}</Alert>:<Table><TableHead><TableRow>{columns.map(column=><TableCell key={column} sx={{fontWeight:800}}>{t(`clientEvidence.columns.${column}`,{defaultValue:column.replaceAll('_',' ')})}</TableCell>)}<TableCell>{t('clientEvidence.source')}</TableCell></TableRow></TableHead><TableBody>{evidence.rows.map((row,index)=><TableRow hover key={index} onClick={()=>row.route&&navigate(String(row.route))} sx={{cursor:row.route?'pointer':'default'}}>{columns.map(column=><TableCell key={column}>{formatValue(column,row[column])}</TableCell>)}<TableCell>{Boolean(row.route)&&<OpenInNew fontSize="small" color="primary"/>}</TableCell></TableRow>)}</TableBody></Table>}</Paper></Stack>
}
