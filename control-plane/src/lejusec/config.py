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

    # 서버 바인드
    host: str = "127.0.0.1"
    port: int = 8000

    # mTLS: 세 값이 모두 설정되면 상호 TLS(클라이언트 인증서 요구)로 기동한다.
    tls_certfile: str = ""
    tls_keyfile: str = ""
    tls_ca_certs: str = ""
    tls_require_client_cert: bool = True

    # GUI(운영자 콘솔)용 CORS 허용 출처. 기본값은 Vite 개발 서버.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # 운영자 토큰(RBAC). "token:role,token:role" 형식. 비우면 인증 비활성(개발).
    # role은 admin(쓰기 허용) 또는 viewer(읽기 전용).
    operator_tokens: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def operator_token_map(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for pair in self.operator_tokens.split(","):
            token, _, role = pair.strip().partition(":")
            if token:
                result[token] = role.strip() or "viewer"
        return result


settings = Settings()
