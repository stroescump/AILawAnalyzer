from fastapi import APIRouter, Request

from app.features.documents.service import DocumentsService

router = APIRouter(prefix="/runs", tags=["evidence"])


@router.get("/{run_id}/evidence")
async def list_evidence(request: Request, run_id: int) -> dict[str, object]:
    conn = request.app.state.db
    return await DocumentsService(conn=conn).list_evidence(run_id=run_id)
