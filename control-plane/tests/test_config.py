from pathlib import Path

from lejusec.config import _default_sqlite_url


def test_default_sqlite_url_is_absolute_and_cwd_independent() -> None:
    """기본 SQLite 경로는 CWD가 아니라 패키지 기준 절대 경로여야 한다."""
    url = _default_sqlite_url()
    assert url.startswith("sqlite:///")
    db_path = Path(url.removeprefix("sqlite:///"))
    assert db_path.is_absolute()
    assert db_path.name == "lejusec-dev.db"
    # control-plane/ 아래로 고정 (config.py 기준 parents[2]).
    assert db_path.parent == Path(__file__).resolve().parents[1]
