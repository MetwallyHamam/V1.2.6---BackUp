# Support Hub AI Cloud Server Deployment Guide

**Platform:** Windows Server, IIS, Ollama, Python, and `qwen2.5:7b`  
**Public application URL:** `https://support.example.com/SupportHub`  
**Document version:** 1.0, September 2026

> Replace `support.example.com` with the real production DNS name before deployment.

## 1. Deployment objective

This guide prepares a new Windows cloud server to run Millensys Support Hub and its local AI model securely.

The public website uses HTTPS through IIS. The Local AI gateway and Ollama remain private on the server and communicate over the loopback interface.

```text
Internet users
    |
    | HTTPS TCP 443
    v
IIS and Support Hub
    |
    | HTTP 127.0.0.1:8090
    v
Local AI gateway
    |
    | HTTP 127.0.0.1:11434
    v
Ollama and qwen2.5:7b
```

Do not expose ports `8090` or `11434` to the internet. The current Local AI endpoints do not provide independent client authentication.

## 2. Recommended server capacity

- Current, fully patched Windows Server.
- 4 to 8 CPU cores.
- 16 GB RAM minimum; 32 GB preferred.
- At least 30 GB of available disk space.
- Static public IP address.
- Production DNS name.
- A supported NVIDIA GPU with at least 8 GB VRAM is strongly preferred for responsive inference.
- Current NVIDIA drivers when using an NVIDIA GPU.

## 3. Network and firewall preparation

Configure the cloud firewall and Windows Firewall as follows:

| Port | Exposure | Purpose | Required control |
|---:|---|---|---|
| 443 | Public | Support Hub HTTPS | Trusted certificate and IIS binding |
| 80 | Optional public | Certificate validation and HTTPS redirect | Redirect application traffic to HTTPS |
| 3389 | Restricted | Windows administration | Permit only VPN or named administrator IPs |
| 8090 | Loopback only | Local AI gateway | Do not create an inbound rule |
| 11434 | Loopback only | Ollama API | Do not create an inbound rule |
| 1433 | Private only | SQL Server | Permit only required private sources |

Create the required storage directories:

```powershell
New-Item -ItemType Directory -Path "E:\SupportHub\Release" -Force
New-Item -ItemType Directory -Path "E:\SupportHub\Storage\attachments" -Force
New-Item -ItemType Directory -Path "E:\SupportHub\Storage\backups" -Force
New-Item -ItemType Directory -Path "E:\SupportHub\OllamaModels" -Force
```

## 4. Configure DNS and HTTPS

### 4.1 Create the DNS record

Create an `A` record pointing the production hostname to the cloud server public IP:

```text
support.example.com    A    CLOUD_PUBLIC_IP
```

### 4.2 Configure IIS

1. Install IIS and the components required by the Support Hub release.
2. Install a TLS certificate trusted by client devices.
3. Bind the certificate to the Support Hub IIS site on TCP port `443`.
4. Configure the production hostname in the HTTPS binding.
5. Redirect HTTP traffic to HTTPS.
6. Verify that login and API requests do not load mixed HTTP content.

The public application URL should be:

```text
https://support.example.com/SupportHub
```

## 5. Install Python

Install 64-bit Python 3.12 for all users. Enable the Python launcher and PATH options during installation.

Open a new Administrator PowerShell window and verify:

```powershell
py -3.12 --version
```

Do not copy a Python virtual environment from another computer. Virtual environments contain machine-specific executable paths and native packages.

## 6. Install and configure Ollama

### 6.1 Install Ollama

Download and install Ollama using the official Windows package:

<https://docs.ollama.com/windows>

Open a new PowerShell window and verify:

```powershell
ollama --version
```

If the command is not found, check the default per-user installation:

```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" --version
```

### 6.2 Configure Ollama

Set machine-level environment variables so the production service account receives them:

```powershell
[Environment]::SetEnvironmentVariable(
    "OLLAMA_MODELS",
    "E:\SupportHub\OllamaModels",
    "Machine"
)

[Environment]::SetEnvironmentVariable(
    "OLLAMA_NO_CLOUD",
    "1",
    "Machine"
)

[Environment]::SetEnvironmentVariable(
    "OLLAMA_HOST",
    "127.0.0.1:11434",
    "Machine"
)
```

These settings:

- Store model data on the application data volume.
- Disable optional Ollama cloud features.
- Keep the Ollama API on the local server only.

Restart Ollama or restart Windows after setting the variables.

### 6.3 Download the AI model

Start Ollama:

```powershell
ollama serve
```

Keep that terminal open. In a second Administrator PowerShell window, run:

```powershell
ollama pull qwen2.5:7b
ollama list
```

Confirm that `qwen2.5:7b` appears in the model list.

### 6.4 Test direct inference

```powershell
$body = @{
    model  = "qwen2.5:7b"
    prompt = "Return exactly: AI model is ready"
    stream = $false
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri "http://127.0.0.1:11434/api/generate" `
    -ContentType "application/json" `
    -Body $body
```

Check whether Ollama is using the CPU or GPU:

```powershell
ollama ps
```

The `PROCESSOR` column reports CPU, GPU, or mixed processing.

## 7. Deploy the Local AI gateway

Copy the release Local AI directory to:

```text
E:\SupportHub\Release\local-ai
```

Do not copy an existing `venv` directory from another server.

### 7.1 Stop an old Local AI process

If this is a replacement installation, locate processes using the old environment:

```powershell
$aiPath = "E:\SupportHub\Release\local-ai"

$processes = Get-CimInstance Win32_Process |
    Where-Object { $_.ExecutablePath -like "$aiPath\venv\*" }

$processes | Select-Object ProcessId, Name, ExecutablePath, CommandLine
```

Stop only the displayed Local AI processes:

```powershell
$processes | ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force
}
```

### 7.2 Build the virtual environment

```powershell
cd "E:\SupportHub\Release\local-ai"

if (Test-Path ".\venv") {
    Remove-Item -LiteralPath ".\venv" -Recurse -Force
}

py -3.12 -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 7.3 Configure Local AI

Create or verify this file:

```text
E:\SupportHub\Release\local-ai\.env
```

Its contents should be:

```env
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT_SECONDS=120
```

### 7.4 Start Local AI

For a same-server deployment, bind the gateway to loopback:

```powershell
cd "E:\SupportHub\Release\local-ai"
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8090
```

Alternatively, use the release startup script:

```powershell
.\run.bat
```

Test the gateway:

```powershell
Invoke-RestMethod "http://127.0.0.1:8090/health"
```

Expected result:

```text
status  service
------  -------
ok      Support Hub Local AI
```

## 8. Configure the Support Hub backend

Use the real HTTPS hostname in the deployed backend `web.config`.

```xml
<environmentVariable name="APP_ENV" value="production" />

<environmentVariable
  name="FRONTEND_ORIGIN"
  value="https://support.example.com" />

<environmentVariable
  name="FRONTEND_BASE_URL"
  value="https://support.example.com/SupportHub" />

<environmentVariable
  name="TRUSTED_HOSTS"
  value="support.example.com,localhost,127.0.0.1" />

<environmentVariable name="LOCAL_AI_ENABLED" value="true" />

<environmentVariable
  name="LOCAL_AI_BASE_URL"
  value="http://127.0.0.1:8090" />

<environmentVariable
  name="LOCAL_AI_TIMEOUT_SECONDS"
  value="120" />
```

When IIS, Local AI, and Ollama run on the same server, do not change `LOCAL_AI_BASE_URL` to the public HTTPS URL.

Replace every deployment secret and credential with a newly issued production value. Store authoritative secrets in an approved password vault and restrict access to `web.config`.

Restart the IIS application pool after deployment. A full restart can be performed during a controlled maintenance window:

```powershell
iisreset
```

## 9. Configure automatic startup

Interactive PowerShell windows are suitable only for installation tests. In production, run Ollama and Local AI under a dedicated Windows service account.

| Service | Startup command | Required access |
|---|---|---|
| Ollama | `ollama serve` | Read/write access to `E:\SupportHub\OllamaModels`, GPU access, and machine environment variables |
| Local AI | `E:\SupportHub\Release\local-ai\run.bat` | Read/execute release files and connect to `127.0.0.1:11434` |

Configure both services with:

- Automatic startup.
- Restart after failure.
- Output directed to a monitored log location.
- A documented, dedicated service account.
- Delayed startup or dependency ordering so Ollama starts before Local AI.

The account running Ollama must be the same account that owns or can access the selected model directory.

## 10. Validate the complete deployment

### 10.1 Test local services

```powershell
Test-NetConnection 127.0.0.1 -Port 11434
Test-NetConnection 127.0.0.1 -Port 8090

Invoke-RestMethod "http://127.0.0.1:11434/api/tags"
Invoke-RestMethod "http://127.0.0.1:8090/health"

ollama list
ollama ps
```

### 10.2 Test the public HTTPS application

```powershell
Invoke-WebRequest "https://support.example.com/SupportHub"
```

From a computer outside the cloud network, verify:

- DNS resolves to the correct public IP.
- The certificate chain is trusted.
- The certificate hostname and expiration date are correct.
- HTTP redirects to HTTPS.
- The application returns a successful HTTP response.

### 10.3 Test AI from Support Hub

1. Sign in through the production HTTPS URL.
2. Create a controlled ticket containing non-sensitive sample data.
3. Run AI intake and confirm that a title and structured description are returned.
4. Run AI resolution and confirm that the request completes within the configured timeout.
5. Review logs for `502`, connection, model-not-found, timeout, or process-restart errors.

## 11. Acceptance checklist

- [ ] The production hostname resolves to the cloud server public IP.
- [ ] A trusted certificate is bound to IIS on TCP 443.
- [ ] HTTP redirects to HTTPS.
- [ ] Ports 8090 and 11434 are not publicly accessible.
- [ ] Ollama responds on `127.0.0.1:11434`.
- [ ] `qwen2.5:7b` appears in `ollama list`.
- [ ] The model answers the direct inference test.
- [ ] Local AI health responds on `127.0.0.1:8090`.
- [ ] `LOCAL_AI_BASE_URL` is `http://127.0.0.1:8090`.
- [ ] AI intake works through the Support Hub interface.
- [ ] AI resolution works through the Support Hub interface.
- [ ] Ollama and Local AI start automatically after a controlled reboot.
- [ ] Previously exposed credentials have been rotated.
- [ ] Service failures and disk usage generate operational alerts.
- [ ] Configuration and application data are covered by backups.

## 12. Troubleshooting

### Local AI health on port 8090 fails

Possible causes:

- Local AI is stopped.
- The virtual environment was copied from another computer.
- Python dependencies were not installed.
- Another process already uses port 8090.

Checks:

```powershell
Get-NetTCPConnection -LocalPort 8090 -ErrorAction SilentlyContinue
Get-Process python -ErrorAction SilentlyContinue
```

Rebuild `venv` locally with Python 3.12 if required.

### Ollama API on port 11434 fails

Possible causes:

- Ollama is not installed for the production account.
- `ollama serve` is not running.
- The service is using a different user environment.

Checks:

```powershell
Get-Command ollama -ErrorAction SilentlyContinue
Get-NetTCPConnection -LocalPort 11434 -ErrorAction SilentlyContinue
Get-Process ollama -ErrorAction SilentlyContinue
```

### Model not found

Verify the active model directory and model list:

```powershell
[Environment]::GetEnvironmentVariable("OLLAMA_MODELS", "Machine")
ollama list
ollama pull qwen2.5:7b
```

### Access denied while deleting venv

Python has loaded files from the environment. Stop the Local AI process or Windows service before deleting `venv`.

### Support Hub returns 502

Test each dependency in order:

```powershell
Invoke-RestMethod "http://127.0.0.1:11434/api/tags"
Invoke-RestMethod "http://127.0.0.1:8090/health"
```

Then inspect Ollama, Local AI, and Support Hub logs for connection or timeout errors.

### AI works interactively but fails after reboot

The processes may be tied to an interactive login or running under accounts with different environment variables. Run both components as automatically started services under a documented service account.

### Inference is slow

Run:

```powershell
ollama ps
```

If the model is running on CPU, verify GPU availability, current drivers, service-account GPU access, and available VRAM.

## 13. Separate AI server variation

If Ollama and Local AI must run on a different cloud server:

1. Connect the application and AI servers through a private virtual network or VPN.
2. Keep Ollama on `127.0.0.1:11434` on the AI server.
3. Bind Local AI port 8090 only to the AI server private interface.
4. Restrict port 8090 so only the Support Hub application server can connect.
5. Add API authentication or mutual TLS before production use.
6. Do not expose Local AI or Ollama directly to the internet.

Only in this architecture should the Support Hub configuration use a private AI server address:

```xml
<environmentVariable
  name="LOCAL_AI_BASE_URL"
  value="http://10.20.0.15:8090" />
```

The public Support Hub HTTPS URL still does not need to expose either AI port.

## 14. Operational maintenance

- Review Windows, IIS, Support Hub, Local AI, and Ollama logs after deployments and restarts.
- Monitor disk use for models, attachments, backups, and logs.
- Test AI intake and resolution after every Ollama, model, Python, or application upgrade.
- Apply upgrades during a maintenance window.
- Retain a rollback copy of application configuration.
- Back up configuration and business data.
- Periodically review service-account permissions.
- Remove interactive logon permission from service accounts where operationally practical.

## 15. Official references

- [Ollama Windows installation](https://docs.ollama.com/windows)
- [Ollama configuration and networking](https://docs.ollama.com/faq)
- [Ollama API introduction](https://docs.ollama.com/api/introduction)
- [Microsoft IIS reverse proxy with URL Rewrite and ARR](https://learn.microsoft.com/en-us/iis/extensions/url-rewrite-module/reverse-proxy-with-url-rewrite-v2-and-application-request-routing)
