# Local AI deployment

Support Hub uses retrieval-augmented generation (RAG), not a frozen fine-tune. On each request the backend securely selects the most relevant verified resolutions from the connected Support Hub database and sends at most five examples to the local model. New resolved tickets therefore become available automatically; there is no export or retraining job.

Retrieval is restricted to the same client and, when available, the same product or module. This prevents one client's ticket history from being exposed in another client's suggestion. The model only suggests content; a user must review and submit it.

## Server components

Install these on the application server (or use a dedicated internal AI server):

1. Ollama for Windows.
2. Python 3.12 or newer for the `local-ai` service.
3. The model: `ollama pull qwen2.5:7b`.

The `local-ai` directory is portable and can be copied to any local drive or directory, or to a separate internal AI server. It does not need to remain inside the Support Hub website or release directory. From whichever directory you choose:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8090
```

Run Ollama and the local AI API under dedicated Windows service accounts and configure automatic restart. Keep port `11434` bound to loopback. When all components share a server, port `8090` can also use loopback. If the AI service is on another internal server, bind port `8090` to `0.0.0.0`, permit only the Support Hub server through the firewall, and change `LOCAL_AI_BASE_URL` in the backend environment.

`run.bat` resolves its own directory before loading the virtual environment and `.env`, so it also works when launched from another working directory. After moving the folder, recreate `venv` if its Python paths no longer match the destination. No Support Hub database change is required.

## Database and release behavior

The AI service does not connect to SQL Server and does not contain database credentials. The authenticated Support Hub backend reads permitted ticket evidence using its normal `DATABASE_URL`, performs retrieval, and calls the AI service. Consequently:

- a release package contains the AI service source but never the Ollama model or database data;
- the destination server must pull/copy the configured Ollama model separately;
- changing SQL Server only requires changing the backend `DATABASE_URL`;
- no database migration or AI re-index is required for this retrieval implementation;
- when local AI is unavailable, normal ticket intake and resolution remain usable.

## Verification

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
Invoke-RestMethod http://127.0.0.1:8090/health
```

Then sign in to Support Hub and test **Improve and classify with local AI** and **Draft resolution with local AI** using a non-production ticket before enabling users.
