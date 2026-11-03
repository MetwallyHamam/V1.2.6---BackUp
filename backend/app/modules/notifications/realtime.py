from datetime import timedelta
from typing import Any

import jwt

from app.core.clock import server_now
from app.core.config import get_settings


class RealtimeTicketStore:
    """Issue short-lived, signed WebSocket tickets that work across API workers."""

    def issue(self, user_id: int, lifetime_seconds: int = 30) -> str:
        now = server_now()
        payload = {
            "sub": str(user_id),
            "type": "notifications_websocket",
            "iat": now,
            "exp": now + timedelta(seconds=lifetime_seconds),
        }
        return jwt.encode(payload, get_settings().secret_key, algorithm="HS256")

    def consume(self, token: str) -> int | None:
        try:
            payload: dict[str, Any] = jwt.decode(
                token,
                get_settings().secret_key,
                algorithms=["HS256"],
            )
            if payload.get("type") != "notifications_websocket":
                return None
            return int(payload["sub"])
        except (jwt.PyJWTError, KeyError, TypeError, ValueError):
            return None


realtime_tickets = RealtimeTicketStore()
