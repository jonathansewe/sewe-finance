"""Response body for GET /sessions (Settings → Active sessions, D-22)."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class SessionOut(BaseModel):
    id: uuid.UUID
    device: str  # "Chrome on Windows"
    created_at: datetime
    last_seen_at: datetime
    current: bool  # "this session" marker
