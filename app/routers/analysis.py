"""Analysis API: upload audio, run the pipeline, fetch/list reports."""
import logging
import os
import tempfile

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import CurrentPrincipal, get_current_principal
from app.core.rate_limit import enforce_rate_limit
from app.database import get_db
from app.models import Analysis
from app.schemas import AnalysisListItem, AnalysisOut
from app.services.pipeline import cache_report, get_cached_report, run_pipeline

logger = logging.getLogger("vocal_vantage.analysis")
router = APIRouter(prefix="/api/analyses", tags=["analyses"])


def _validate_upload(file: UploadFile) -> str:
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
    if ext not in settings.allowed_extensions_set:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '.{ext}'. Allowed: {', '.join(sorted(settings.allowed_extensions_set))}",
        )
    return ext


async def _save_temp(file: UploadFile, ext: str) -> str:
    fd, path = tempfile.mkstemp(suffix=f".{ext}")
    size = 0
    try:
        with os.fdopen(fd, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds {settings.max_upload_mb} MB limit.",
                    )
                out.write(chunk)
    except Exception:
        if os.path.exists(path):
            os.remove(path)
        raise
    if size == 0:
        os.remove(path)
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    return path


def _owner_filter(principal: CurrentPrincipal):
    if principal.is_guest:
        return Analysis.guest_token == principal.guest_token
    return Analysis.user_id == principal.user_id


@router.post("", response_model=AnalysisOut, status_code=status.HTTP_201_CREATED)
async def create_analysis(
    request: Request,
    file: UploadFile = File(...),
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    await enforce_rate_limit(request)
    ext = _validate_upload(file)
    temp_path = await _save_temp(file, ext)

    record = Analysis(
        filename=file.filename or f"recording.{ext}",
        status="processing",
        user_id=None if principal.is_guest else principal.user_id,
        guest_token=principal.guest_token if principal.is_guest else None,
    )
    db.add(record)
    await db.flush()

    try:
        result = await run_pipeline(temp_path, record.filename)
        analysis = result["analysis"]
        report = result["report"]

        record.status = "done"
        record.transcript = analysis.transcript
        record.duration_seconds = analysis.duration_seconds
        record.word_count = analysis.word_count
        record.words_per_minute = analysis.words_per_minute
        record.filler_count = analysis.filler_count
        record.fluency_score = analysis.fluency_score
        record.report = report
        await db.flush()
        await cache_report(record.id, report)
    except Exception as exc:
        logger.exception("Pipeline failed: %s", exc)
        record.status = "failed"
        record.error_message = str(exc)[:500]
        await db.flush()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Audio processing failed: {exc}",
        )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return record


@router.get("", response_model=list[AnalysisListItem])
async def list_analyses(
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.scalars(
        select(Analysis).where(_owner_filter(principal)).order_by(Analysis.created_at.desc()).limit(50)
    )
    return list(rows)


@router.get("/{analysis_id}", response_model=AnalysisOut)
async def get_analysis(
    analysis_id: str,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    record = await db.scalar(
        select(Analysis).where(Analysis.id == analysis_id, _owner_filter(principal))
    )
    if not record:
        raise HTTPException(status_code=404, detail="Analysis not found.")

    # Serve report from Redis cache when available.
    if record.report is None:
        cached = await get_cached_report(analysis_id)
        if cached:
            record.report = cached
    return record


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analysis(
    analysis_id: str,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    record = await db.scalar(
        select(Analysis).where(Analysis.id == analysis_id, _owner_filter(principal))
    )
    if not record:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    await db.delete(record)
    return None
