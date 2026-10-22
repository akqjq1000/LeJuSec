"""개발용 mTLS 인증서 생성 CLI (로직: lejusec.certs.generate_dev_certs).

예:
  python scripts/gen_certs.py --out ../certs \\
      --server-san DNS:localhost --server-san IP:127.0.0.1 --server-san IP:192.168.143.20
"""

import argparse
from pathlib import Path

from lejusec.certs import generate_dev_certs


def main() -> None:
    parser = argparse.ArgumentParser(description="generate dev mTLS certs (CA/server/client)")
    parser.add_argument("--out", default="certs", help="output directory")
    parser.add_argument(
        "--server-san",
        action="append",
        default=[],
        metavar="DNS:host|IP:addr",
        help="server certificate SAN (repeatable)",
    )
    parser.add_argument("--days", type=int, default=825)
    args = parser.parse_args()

    generate_dev_certs(Path(args.out), args.server_san or None, args.days)
    print(f"wrote ca.crt/server.crt/client.crt (+ keys) to {args.out}/")


if __name__ == "__main__":
    main()
