"""런타임 설정. 환경변수(`LEJUSEC_*`) 또는 `.env`에서 로드한다.

비밀값은 .env/시크릿 매니저에서만 주입하며 기본값은 로컬 개발용이다.
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_sqlite_url() -> str:
    """CWD와 무관한 고정 SQLite 경로.

    과거 기본값 `sqlite:///./lejusec-dev.db`는 실행 시점의 작업 디렉터리에 상대적이라,
    저장소 루트에서 띄웠을 때와 control-plane/에서 띄웠을 때 서로 다른(빈) DB가 열려
    "등록 자산이 사라진 것처럼" 보이는 문제가 있었다. 패키지 기준 절대 경로로 고정한다.
    """
    # config.py: control-plane/src/lejusec/config.py → parents[2] == control-plane/
    root = Path(__file__).resolve().parents[2]
    return f"sqlite:///{(root / 'lejusec-dev.db').as_posix()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LEJUSEC_", env_file=".env", extra="ignore")

    # 기본값은 바로 실행 가능한 로컬 SQLite(패키지 기준 고정 경로, CWD 무관). 운영/compose에서는
    # LEJUSEC_DATABASE_URL 로 PostgreSQL(postgresql+psycopg://...)을 주입한다.
    database_url: str = Field(default_factory=_default_sqlite_url)
    vector_db_url: str = "http://localhost:6333"
    log_level: str = "INFO"

    # 서버 바인드. 기본 0.0.0.0 — 다른 호스트의 에이전트가 접속할 수 있도록 모든
    # 인터페이스에 바인드한다. 루프백만 열려면 LEJUSEC_HOST=127.0.0.1 로 덮어쓴다.
    # 운영 환경에서는 방화벽/TLS로 접근을 제한한다.
    host: str = "0.0.0.0"
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

    # RAG 근거 검색 백엔드: "embedding"(기본, 해싱 벡터 코사인) | "lexical"(토큰 겹침).
    rag_backend: str = "embedding"

    # 조치 생성 백엔드: "template"(기본, 지식베이스) | "llm"(Claude; 실패 시 템플릿 폴백).
    generator_backend: str = "template"
    llm_api_key: str = ""
    llm_model: str = "claude-opus-5-5"

    # 샌드박스 검증 백엔드: "dry-run"(기본, 정적 재확인) | "container"(Docker 실제 적용).
    sandbox_backend: str = "dry-run"
    sandbox_image: str = "ubuntu:24.04"
    sandbox_timeout: int = 120

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
