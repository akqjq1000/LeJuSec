"""mTLS 지원 실행 진입점.

TLS 인증서(cert/key)가 설정되면 uvicorn을 TLS로 기동하고, CA가 함께 설정되면
클라이언트 인증서를 요구(상호 TLS)한다. 설정이 없으면 평문 HTTP로 기동한다.

예 (상호 TLS):
  LEJUSEC_TLS_CERTFILE=../certs/server.crt \\
  LEJUSEC_TLS_KEYFILE=../certs/server.key \\
  LEJUSEC_TLS_CA_CERTS=../certs/ca.crt \\
  python -m lejusec.server
"""

import ssl

import uvicorn

from lejusec.config import settings


def main() -> None:
    if settings.tls_certfile and settings.tls_keyfile:
        cert_reqs = ssl.CERT_REQUIRED if settings.tls_require_client_cert else ssl.CERT_OPTIONAL
        uvicorn.run(
            "lejusec.main:app",
            host=settings.host,
            port=settings.port,
            ssl_certfile=settings.tls_certfile,
            ssl_keyfile=settings.tls_keyfile,
            ssl_ca_certs=settings.tls_ca_certs or None,
            ssl_cert_reqs=int(cert_reqs),
        )
    else:
        uvicorn.run("lejusec.main:app", host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
