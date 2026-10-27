"""데이터베이스 엔진·세션 구성."""

from collections.abc import Iterator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from lejusec.config import settings
from lejusec.models import Base

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

# 신규 추가 컬럼의 경량 마이그레이션(개발용). create_all은 기존 테이블에 컬럼을
# 추가하지 않으므로, 기존 DB에도 안전하게 반영되도록 누락 컬럼만 ALTER로 보강한다.
# (table, column, DDL 타입/기본값). 운영은 정식 마이그레이션 도구로 대체.
_COLUMN_MIGRATIONS = [
    ("assets", "asset_group", "VARCHAR(64) DEFAULT ''"),
    ("assets", "address", "VARCHAR(255) DEFAULT ''"),
    ("assets", "last_seen_at", "TIMESTAMP"),
    ("assets", "scan_paused", "BOOLEAN DEFAULT 0"),
]


def _apply_column_migrations() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table, column, ddl in _COLUMN_MIGRATIONS:
            if table not in tables:
                continue
            existing = {c["name"] for c in inspector.get_columns(table)}
            if column not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))


def init_db() -> None:
    """테이블을 생성한다 (없을 때만). 초기 개발용; 운영은 마이그레이션 도구로 대체."""
    Base.metadata.create_all(engine)
    _apply_column_migrations()


def get_session() -> Iterator[Session]:
    """요청 범위 DB 세션 (FastAPI 의존성)."""
    with SessionLocal() as session:
        yield session
