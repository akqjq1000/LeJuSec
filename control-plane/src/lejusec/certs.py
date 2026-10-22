"""개발용 mTLS 인증서 생성 (자가 CA / 서버 / 클라이언트).

운영에서는 사내 PKI/ACME로 대체한다. 여기서는 로컬·테스트용 자가 CA를 만들어
서버 인증서(SERVER_AUTH)와 에이전트 클라이언트 인증서(CLIENT_AUTH)를 발급한다.
개인키(.key)는 .gitignore로 커밋되지 않는다.
"""

from __future__ import annotations

import datetime as dt
import ipaddress
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def _new_key() -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(ec.SECP256R1())


def _write_key(key: ec.EllipticCurvePrivateKey, path: Path) -> None:
    path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )


def _write_cert(cert: x509.Certificate, path: Path) -> None:
    path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def _parse_sans(items: list[str]) -> x509.SubjectAlternativeName:
    names: list[x509.GeneralName] = []
    for item in items:
        kind, _, value = item.partition(":")
        if kind.upper() == "DNS":
            names.append(x509.DNSName(value))
        elif kind.upper() == "IP":
            names.append(x509.IPAddress(ipaddress.ip_address(value)))
        else:
            raise ValueError(f"invalid SAN (use DNS:... or IP:...): {item!r}")
    return x509.SubjectAlternativeName(names)


def _key_usage(*, cert_sign: bool) -> x509.KeyUsage:
    return x509.KeyUsage(
        digital_signature=not cert_sign,
        key_cert_sign=cert_sign,
        crl_sign=cert_sign,
        content_commitment=False,
        key_encipherment=False,
        data_encipherment=False,
        key_agreement=False,
        encipher_only=False,
        decipher_only=False,
    )


def generate_dev_certs(
    out_dir: Path,
    server_sans: list[str] | None = None,
    days: int = 825,
) -> None:
    """CA/서버/클라이언트 인증서·키를 out_dir에 PEM으로 생성한다."""
    out_dir.mkdir(parents=True, exist_ok=True)
    sans = _parse_sans(server_sans or ["DNS:localhost", "IP:127.0.0.1"])

    now = dt.datetime.now(dt.UTC)
    not_after = now + dt.timedelta(days=days)

    ca_key = _new_key()
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "LeJuSec Dev CA")])
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(not_after)
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(_key_usage(cert_sign=True), critical=True)
        .sign(ca_key, hashes.SHA256())
    )

    def _leaf(
        common_name: str,
        key: ec.EllipticCurvePrivateKey,
        eku: x509.ObjectIdentifier,
        san: x509.SubjectAlternativeName | None,
    ) -> x509.Certificate:
        builder = (
            x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)]))
            .issuer_name(ca_name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(not_after)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(_key_usage(cert_sign=False), critical=True)
            .add_extension(x509.ExtendedKeyUsage([eku]), critical=False)
        )
        if san is not None:
            builder = builder.add_extension(san, critical=False)
        return builder.sign(ca_key, hashes.SHA256())

    server_key = _new_key()
    server_cert = _leaf("lejusec-control-plane", server_key, ExtendedKeyUsageOID.SERVER_AUTH, sans)
    client_key = _new_key()
    client_cert = _leaf("lejusec-agent", client_key, ExtendedKeyUsageOID.CLIENT_AUTH, None)

    _write_cert(ca_cert, out_dir / "ca.crt")
    _write_key(ca_key, out_dir / "ca.key")
    _write_cert(server_cert, out_dir / "server.crt")
    _write_key(server_key, out_dir / "server.key")
    _write_cert(client_cert, out_dir / "client.crt")
    _write_key(client_key, out_dir / "client.key")
