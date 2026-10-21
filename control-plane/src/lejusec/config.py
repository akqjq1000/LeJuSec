"""런타임 설정. 환경변수(`LEJUSEC_*`) 또는 `.env`에서 로드한다.

비밀값은 .env/시크릿 매니저에서만 주입하며 기본값은 로컬 개발용이다.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LEJUSEC_", env_file=".env", extra="ignore")

    # 기본값은 바로 실행 가능한 로컬 SQLite. 운영/compose에서는
    # LEJUSEC_DATABASE_URL 로 PostgreSQL(postgresql+psycopg://...)을 주입한다.
    database_url: str = "sqlite:///./lejusec-dev.db"
    vector_db_url: str = "http://localhost:6333"
    log_level: str = "INFO"


settings = Settings()
