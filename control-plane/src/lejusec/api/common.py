"""API 공통 헬퍼: 자산 조회와 서명 본문 검증."""

import datetime as dt

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from lejusec.models import Asset
from lejusec.signing import verify_ed25519


def get_or_404(session: Session, asset_id: int) -> Asset:
    asset = session.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="asset not found")
    return asset


async def read_signed_body(asset: Asset, request: Request) -> bytes:
    """등록된 공개키로 X-Signature(전송 바디 원본 바이트 서명)를 검증하고 바디를 반환."""
    if not asset.public_key:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="no public key registered for asset")
    signature = request.headers.get("X-Signature", "")
    raw = await request.body()
    if not signature or not verify_ed25519(asset.public_key, raw, signature):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid or missing signature")
    # 서명이 검증된 모든 요청에서 헬스체크용 마지막 통신 시각을 갱신한다(커밋은 호출자).
    asset.last_seen_at = dt.datetime.now(dt.UTC)
    return raw


def client_ip(request: Request) -> str:
    """요청 소스 IP(프록시의 X-Forwarded-For 우선). 주소 자동 기록 폴백용."""
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else ""
