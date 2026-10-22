"""Ed25519 서명 검증.

에이전트는 전송 바디(원본 JSON 바이트)에 서명하고, 컨트롤 플레인은 등록된
공개키로 그 바이트에 대한 서명을 검증한다. 정규화(canonicalization) 불일치를
피하기 위해 '전송된 바이트 그대로'를 서명 대상으로 삼는다.
"""

import base64
import binascii

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


def verify_ed25519(public_key_b64: str, message: bytes, signature_b64: str) -> bool:
    """base64 공개키로 message(raw bytes)에 대한 base64 서명을 검증한다."""
    try:
        pub = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64, validate=True))
        signature = base64.b64decode(signature_b64, validate=True)
    except (ValueError, binascii.Error):
        return False
    try:
        pub.verify(signature, message)
    except InvalidSignature:
        return False
    return True
