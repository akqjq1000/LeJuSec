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
    public_key: str
    last_scan_at: dt.datetime | None
    created_at: dt.datetime


class KeyIn(BaseModel):
    # Ed25519 공개키 (base64, 32바이트 → 44자)
    public_key: str = Field(min_length=1, max_length=128)


class PackageIn(BaseModel):
    name: str
    version: str = ""
    source: str = ""


class ProcessIn(BaseModel):
    pid: int
    name: str = ""
    exe: str = ""


class InventoryIn(BaseModel):
    packages: list[PackageIn] = Field(default_factory=list)
    processes: list[ProcessIn] = Field(default_factory=list)


class InventoryAck(BaseModel):
    snapshot_id: int
    package_count: int
    process_count: int
    captured_at: dt.datetime
