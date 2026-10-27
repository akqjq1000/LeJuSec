#!/usr/bin/env python3
"""LeJuSec 개발 서버 일괄 실행기.

컨트롤 플레인(API)과 웹 콘솔(Vite)을 한 번에 띄우고, 두 프로세스의 출력을
접두어([cp]/[web])로 합쳐서 보여준다. Ctrl+C 한 번으로 둘 다 종료한다.

사용:
    python scripts/dev.py            # 둘 다 실행 (기본)
    python scripts/dev.py --tls      # 컨트롤 플레인을 mTLS로 실행 (certs/ 필요)
    python scripts/dev.py --no-web   # 컨트롤 플레인만
    python scripts/dev.py --no-cp    # 웹 콘솔만

전제: control-plane 의존성 설치(`make cp-install`)와 web 의존성 설치(`npm install`).
컨트롤 플레인은 control-plane/.venv 가 있으면 그 파이썬을, 없으면 현재 파이썬을 쓴다.
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROL_PLANE = ROOT / "control-plane"
WEB = ROOT / "web"
CERTS = ROOT / "certs"


def _cp_python() -> str:
    """control-plane 전용 venv 파이썬이 있으면 그것을, 없으면 현재 파이썬을 쓴다."""
    candidates = [
        CONTROL_PLANE / ".venv" / "Scripts" / "python.exe",  # Windows
        CONTROL_PLANE / ".venv" / "bin" / "python",  # Linux/macOS
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def _npm() -> str | None:
    """npm 실행 파일 경로(Windows는 npm.cmd)."""
    return shutil.which("npm") or shutil.which("npm.cmd")


def _pump(prefix: str, stream: object, color: str) -> None:
    """자식 프로세스 출력 라인마다 접두어를 붙여 중계한다."""
    reset = "\033[0m"
    for raw in iter(stream.readline, ""):  # type: ignore[attr-defined]
        try:
            line = raw.rstrip("\n")
        except UnicodeDecodeError:
            # 만약 디코딩 에러가 발생하면 대체 문자로 처리한다.
            line = raw.encode("utf-8", errors="replace").decode("utf-8").rstrip("\n")
        sys.stdout.write(f"{color}[{prefix}]{reset} {line}\n")
        sys.stdout.flush()


def _spawn(
    name: str, args: list[str], cwd: Path, env: dict[str, str], color: str
) -> subprocess.Popen:
    proc = subprocess.Popen(
        args,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        bufsize=1,
    )
    threading.Thread(target=_pump, args=(name, proc.stdout, color), daemon=True).start()
    return proc


def _cp_env(tls: bool) -> dict[str, str]:
    env = os.environ.copy()
    if tls:
        env["LEJUSEC_TLS_CERTFILE"] = str(CERTS / "server.crt")
        env["LEJUSEC_TLS_KEYFILE"] = str(CERTS / "server.key")
        env["LEJUSEC_TLS_CA_CERTS"] = str(CERTS / "ca.crt")
    return env


def main() -> int:
    parser = argparse.ArgumentParser(description="LeJuSec 개발 서버 일괄 실행기")
    parser.add_argument("--tls", action="store_true", help="컨트롤 플레인 mTLS (certs/ 필요)")
    parser.add_argument("--no-web", action="store_true", help="웹 콘솔을 띄우지 않음")
    parser.add_argument("--no-cp", action="store_true", help="컨트롤 플레인을 띄우지 않음")
    opts = parser.parse_args()

    if opts.tls and not (CERTS / "server.crt").exists():
        print("certs/ 가 없습니다. 먼저 `make certs` 를 실행하세요.", file=sys.stderr)
        return 1

    procs: list[tuple[str, subprocess.Popen]] = []

    if not opts.no_cp:
        print("▶ 컨트롤 플레인 (http%s://127.0.0.1:8000)" % ("s" if opts.tls else ""))
        procs.append(
            (
                "cp",
                _spawn(
                    "cp",
                    [_cp_python(), "-m", "lejusec.server"],
                    CONTROL_PLANE,
                    _cp_env(opts.tls),
                    "\033[36m",  # cyan
                ),
            )
        )

    if not opts.no_web:
        npm = _npm()
        if npm is None:
            print("npm 을 찾을 수 없습니다. Node 20+ 를 설치하세요.", file=sys.stderr)
        else:
            print("▶ 웹 콘솔 (http://localhost:5173)")
            procs.append(
                (
                    "web",
                    # magenta
                    _spawn("web", [npm, "run", "dev"], WEB, os.environ.copy(), "\033[35m"),
                )
            )

    if not procs:
        print("실행할 서버가 없습니다 (--no-cp/--no-web 조합을 확인하세요).", file=sys.stderr)
        return 1

    print("Ctrl+C 로 전체 종료합니다.\n")

    def _shutdown(*_: object) -> None:
        for _name, proc in procs:
            if proc.poll() is None:
                proc.terminate()

    signal.signal(signal.SIGINT, _shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _shutdown)

    # 한 프로세스라도 죽으면 나머지도 정리하고 그 종료 코드를 반환한다.
    exit_code = 0
    try:
        while procs:
            for name, proc in list(procs):
                code = proc.poll()
                if code is not None:
                    print(f"[{name}] 종료됨 (code={code})")
                    if code not in (0, None):
                        exit_code = code
                    procs.remove((name, proc))
                    _shutdown()
            try:
                for _name, proc in procs:
                    proc.wait(timeout=0.3)
            except subprocess.TimeoutExpired:
                pass
    except KeyboardInterrupt:
        _shutdown()
    finally:
        _shutdown()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
