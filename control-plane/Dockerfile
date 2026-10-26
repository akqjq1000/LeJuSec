# LeJuSec 컨트롤 플레인(API/오케스트레이터) 컨테이너 이미지.
# 빌드 컨텍스트: control-plane/
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    # 컨테이너에서는 외부에서 접속 가능하도록 0.0.0.0 바인드
    LEJUSEC_HOST=0.0.0.0 \
    LEJUSEC_PORT=8000

WORKDIR /app

# 의존성 레이어를 소스와 분리해 캐시 효율을 높인다.
COPY pyproject.toml ./
COPY src ./src
RUN pip install .

# 비루트 사용자로 실행
RUN useradd --create-home --uid 10001 lejusec
USER lejusec

EXPOSE 8000

# /healthz 로 상태 확인
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz').status==200 else 1)"

CMD ["python", "-m", "lejusec.server"]
