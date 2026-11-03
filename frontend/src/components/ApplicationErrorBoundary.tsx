import { Alert, Box, Button, Paper, Typography } from '@mui/material'
import { Component, ErrorInfo, ReactNode } from 'react'

type State = { error: Error | null }

export class ApplicationErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Application rendering failed', error, info.componentStack)
  }

  render() {
    if (!this.state.error) return this.props.children
    return <Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center', bgcolor: '#f1f5f9', p: 3 }}>
      <Paper sx={{ maxWidth: 680, p: 4 }}>
        <Typography variant="h5" fontWeight={700} gutterBottom>The page could not be displayed</Typography>
        <Alert severity="error" sx={{ my: 2 }}>{this.state.error.message || 'An unexpected interface error occurred.'}</Alert>
        <Typography color="text.secondary" mb={2}>Reload the latest application files. If the problem continues, copy the error above for support.</Typography>
        <Button variant="contained" onClick={() => window.location.reload()}>Reload application</Button>
      </Paper>
    </Box>
  }
}
