import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from threading import Lock
from typing import Any

from app.core.config import Settings


class GraphConfigurationError(RuntimeError):
    pass


class GraphRequestError(RuntimeError):
    pass


@dataclass
class CachedToken:
    value: str
    expires_at: float


class MicrosoftGraphClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._token: CachedToken | None = None
        self._lock = Lock()

    def configured(self) -> bool:
        return all((
            self.settings.microsoft_graph_tenant_id,
            self.settings.microsoft_graph_client_id,
            self.settings.microsoft_graph_client_secret,
        ))

    def access_token(self) -> str:
        with self._lock:
            if self._token and self._token.expires_at > time.time() + 60:
                return self._token.value
            if not self.configured():
                raise GraphConfigurationError("Microsoft Graph tenant, client ID, and secret are required.")
            tenant = urllib.parse.quote(str(self.settings.microsoft_graph_tenant_id), safe="")
            body = urllib.parse.urlencode({
                "client_id": self.settings.microsoft_graph_client_id,
                "client_secret": self.settings.microsoft_graph_client_secret,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
            }).encode()
            request = urllib.request.Request(
                f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
                data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST",
            )
            payload = self._open_json(request)
            token = payload.get("access_token")
            if not isinstance(token, str) or not token:
                raise GraphRequestError("Microsoft identity response did not contain an access token.")
            expires_in = int(payload.get("expires_in", 3600))
            self._token = CachedToken(token, time.time() + max(300, expires_in))
            return token

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        url = path if path.startswith("https://") else "https://graph.microsoft.com/v1.0/" + path.lstrip("/")
        body = json.dumps(payload).encode() if payload is not None else None
        for attempt in range(3):
            correlation_id = str(uuid.uuid4())
            request = urllib.request.Request(url, data=body, method=method, headers={
                "Authorization": f"Bearer {self.access_token()}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "Millensys-SupportHub/OutlookIntegration",
                "client-request-id": correlation_id,
                "return-client-request-id": "true",
            })
            try:
                return self._open_json(request)
            except urllib.error.HTTPError as exc:
                if exc.code not in {429, 502, 503, 504} or attempt == 2:
                    raise GraphRequestError(f"Microsoft Graph returned HTTP {exc.code}.") from exc
                retry_after = exc.headers.get("Retry-After", "1")
                time.sleep(min(max(int(retry_after) if retry_after.isdigit() else 1, 1), 10))
        raise GraphRequestError("Microsoft Graph request failed after retries.")

    def _open_json(self, request: urllib.request.Request) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(  # noqa: S310 -- fixed Microsoft endpoints or validated delta URL
                request, timeout=self.settings.microsoft_graph_timeout_seconds
            ) as response:
                raw = response.read()
        except urllib.error.HTTPError:
            raise
        except (OSError, TimeoutError) as exc:
            raise GraphRequestError("Microsoft Graph could not be reached.") from exc
        if not raw:
            return {}
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise GraphRequestError("Microsoft Graph returned an invalid response.")
        return value
