"""점검 기준(지식베이스) 조회·RAG 근거 검색 API."""

from fastapi import APIRouter, Query

from lejusec.knowledge import CheckItem, load_checks
from lejusec.rag import retrieve
from lejusec.schemas import CheckItemOut, CheckSearchHit

router = APIRouter(prefix="/checks", tags=["checks"])


def _to_out(item: CheckItem) -> CheckItemOut:
    return CheckItemOut(
        id=item.id,
        standard=item.standard,
        title=item.title,
        severity=item.severity.value,
        rationale=item.rationale,
        category=item.category,
    )


@router.get("", response_model=list[CheckItemOut])
def list_checks() -> list[CheckItemOut]:
    """전체 점검 기준 목록."""
    return [_to_out(item) for item in load_checks()]


@router.get("/search", response_model=list[CheckSearchHit])
def search_checks(
    q: str = Query(..., min_length=1, description="근거 검색 쿼리"),
    k: int = Query(5, ge=1, le=20),
) -> list[CheckSearchHit]:
    """쿼리와 관련된 점검 기준 근거를 점수 순으로 반환(RAG; 설정된 백엔드)."""
    return [CheckSearchHit(item=_to_out(hit.item), score=hit.score) for hit in retrieve(q, k=k)]
