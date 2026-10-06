from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..config import get_settings

from ..database import get_db
from ..dependencies import get_token_payload
from ..exceptions import not_found
from ..models import TaskFile

router = APIRouter(prefix="/api/files", tags=["files"])

@router.get("/{file_id}")
def download_file(
    file_id: int,
    payload: dict = Depends(get_token_payload),
    db: Session = Depends(get_db),
):
    """скачивание файла задания по id для авторизованного клиента"""
    row = db.get(TaskFile, file_id)
    if row is None:
        raise not_found("Файл не найден")

    path = get_settings().task_files_dir / row.file_path
    if not path.exists():
        raise not_found("файл отсутствует на диске")

    return FileResponse(
        path,
        filename=row.original_name,
        media_type=row.mime_type or "application/octet-stream",
    )