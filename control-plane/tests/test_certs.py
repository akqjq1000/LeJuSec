from pathlib import Path

from cryptography import x509
from cryptography.x509.oid import ExtendedKeyUsageOID

from lejusec.certs import generate_dev_certs


def _load(path: Path) -> x509.Certificate:
    return x509.load_pem_x509_certificate(path.read_bytes())


def test_generate_and_chain(tmp_path: Path) -> None:
    generate_dev_certs(tmp_path, ["DNS:localhost", "IP:127.0.0.1", "IP:192.168.143.20"])

    for name in ("ca.crt", "ca.key", "server.crt", "server.key", "client.crt", "client.key"):
        assert (tmp_path / name).exists(), f"missing {name}"

    ca = _load(tmp_path / "ca.crt")
    server = _load(tmp_path / "server.crt")
    client = _load(tmp_path / "client.crt")

    # CA가 서버·클라이언트 인증서를 발급했는지(서명 체인) 검증 — 실패 시 예외.
    server.verify_directly_issued_by(ca)
    client.verify_directly_issued_by(ca)

    srv_eku = server.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
    assert ExtendedKeyUsageOID.SERVER_AUTH in srv_eku
    cli_eku = client.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
    assert ExtendedKeyUsageOID.CLIENT_AUTH in cli_eku

    san = server.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert "localhost" in san.get_values_for_type(x509.DNSName)


def test_server_cert_is_not_ca(tmp_path: Path) -> None:
    generate_dev_certs(tmp_path)
    server = _load(tmp_path / "server.crt")
    bc = server.extensions.get_extension_for_class(x509.BasicConstraints).value
    assert bc.ca is False
