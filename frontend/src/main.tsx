import { QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { App } from './App'
import { AuthProvider } from './auth/AuthContext'
import { ApplicationErrorBoundary } from './components/ApplicationErrorBoundary'
import { GlobalFeedback } from './components/GlobalFeedback'
import { ApplicationTheme } from './theme/ApplicationTheme'
import { LanguageProvider } from './i18n/LanguageProvider'
import './i18n/config'
import './utils/randomUuid'
import './utils/serverTime'
import { queryClient } from './queryClient'

if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    void navigator.serviceWorker.register(`${import.meta.env.BASE_URL}sw.js`, { scope: import.meta.env.BASE_URL })
  })
}

createRoot(document.getElementById('root')!).render(
  <StrictMode><ApplicationErrorBoundary><QueryClientProvider client={queryClient}><BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, '') || '/'}><AuthProvider><LanguageProvider><ApplicationTheme><GlobalFeedback><App /></GlobalFeedback></ApplicationTheme></LanguageProvider></AuthProvider></BrowserRouter></QueryClientProvider></ApplicationErrorBoundary></StrictMode>,
)
