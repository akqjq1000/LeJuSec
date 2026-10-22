"""API 요청/응답 스키마 (Pydantic)."""

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field


class AssetCreate(BaseModel):
    hostname: str = Field(min_length=1, max_length=255)
    os: str = Field(min_length=1, max_length=64)
    os_version: str = Field(default="", max_length=64)
    role: str = Field(default="", max_length=64)


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    hostname: str
    os: str
    os_version: str
    role: str
    managed: bool
    agent_status: str
    last_scan_at: dt.datetime | None
    created_at: dt.datetime
