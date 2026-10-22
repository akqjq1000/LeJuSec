"""API 공통 헬퍼: 자산 조회와 서명 본문 검증."""

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
    return raw
