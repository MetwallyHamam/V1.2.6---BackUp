import { Alert, Box, Button, Paper, Typography } from "@mui/material";
import { Component, type ErrorInfo, type ReactNode } from "react";

type State = { error: Error | null; recovering: boolean };

export const isStaleApplicationChunkError = (error: Error) =>
  /Failed to fetch dynamically imported module|Importing a module script failed|error loading dynamically imported module/i.test(
    error.message,
  );

async function clearStaleApplicationFiles() {
  if ("caches" in window) {
    const keys = await window.caches.keys();
    await Promise.all(keys.map((key) => window.caches.delete(key)));
  }
  if ("serviceWorker" in navigator) {
    const registrations = await navigator.serviceWorker.getRegistrations();
    await Promise.all(registrations.map((registration) => registration.update()));
  }
}

export class ApplicationErrorBoundary extends Component<
  { children: ReactNode },
  State
> {
  state: State = { error: null, recovering: false };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Application rendering failed", error, info.componentStack);
    if (!isStaleApplicationChunkError(error)) return;
    const recoveryKey = `supporthub-chunk-recovery:${error.message}`;
    if (window.sessionStorage.getItem(recoveryKey)) return;
    window.sessionStorage.setItem(recoveryKey, "true");
    this.setState({ recovering: true });
    void clearStaleApplicationFiles().finally(() => window.location.reload());
  }

  private reloadLatest = () => {
    this.setState({ recovering: true });
    void clearStaleApplicationFiles().finally(() => window.location.reload());
  };

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <Box
        sx={{
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          bgcolor: "#f1f5f9",
          p: 3,
        }}
      >
        <Paper sx={{ maxWidth: 680, p: 4 }}>
          <Typography variant="h5" fontWeight={700} gutterBottom>
            {this.state.recovering
              ? "Loading the latest application"
              : "The page could not be displayed"}
          </Typography>
          <Alert
            severity={this.state.recovering ? "info" : "error"}
            sx={{ my: 2 }}
          >
            {this.state.recovering
              ? "Refreshing outdated application files…"
              : this.state.error.message ||
                "An unexpected interface error occurred."}
          </Alert>
          {!this.state.recovering && (
            <>
              <Typography color="text.secondary" mb={2}>
                Reload the latest application files. If the problem continues,
                copy the error above for support.
              </Typography>
              <Button variant="contained" onClick={this.reloadLatest}>
                Reload application
              </Button>
            </>
          )}
        </Paper>
      </Box>
    );
  }
}
