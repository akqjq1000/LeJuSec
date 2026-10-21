"""데이터베이스 엔진·세션 구성."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from lejusec.config import settings
from lejusec.models import Base

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """테이블을 생성한다 (없을 때만). 초기 개발용; 운영은 마이그레이션 도구로 대체."""
    Base.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    """요청 범위 DB 세션 (FastAPI 의존성)."""
    with SessionLocal() as session:
        yield session
