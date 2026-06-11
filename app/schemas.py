from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class RuleResultOut(BaseModel):
    rule_id: str
    rule_name: str
    adheres: bool


class ScanSubmitResponse(BaseModel):
    scan_id: str
    status: str
    cached: bool


class ScanResultResponse(BaseModel):
    scan_id: str
    status: str
    created_at: dt.datetime
    results: list[RuleResultOut]


class HealthResponse(BaseModel):
    status: str
    ollama_reachable: bool
