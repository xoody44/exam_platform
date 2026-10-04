from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_admin
from ..models import User
from ..schemas import (
    AdminFieldOut,
    AdminTaskOut,
    ConversionTableCreateIn,
    ConversionTableOut,
    ConversionTablePatchIn,
    FieldCreateIn,
    FieldPatchIn,
    SettingsOut,
    SettingsPatchIn,
    TaskCreateIn,
    TaskPatchIn,
    TaskFileOut,
    VariantCreateIn,
    VariantDetailOut,
    VariantOut,
    VariantPatchIn,
)
from ..services import admin_content as ac

router = APIRouter(prefix="/api/admin", tags=["admin"])



@router.get("/variants", response_model=list[VariantOut])
def list_variants(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return ac.list_variants(db)


@router.post("/variants", response_model=VariantOut)
def create_variant(
    payload: VariantCreateIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ac.create_variant(db, admin, payload)


@router.get("/variants/{variant_id}", response_model=VariantDetailOut)
def get_variant(
    variant_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ac.get_variant(db, variant_id)


@router.patch("/variants/{variant_id}", response_model=VariantOut)
def patch_variant(
    variant_id: int,
    payload: VariantPatchIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ac.patch_variant(db, admin, variant_id, payload)


@router.post("/variants/{variant_id}/archive", response_model=VariantOut)
def archive_variant(
    variant_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ac.archive_variant(db, admin, variant_id)



@router.get("/variants/{variant_id}/tasks", response_model=list[AdminTaskOut])
def list_tasks(
    variant_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ac.list_tasks(db, variant_id)


@router.post("/variants/{variant_id}/tasks", response_model=AdminTaskOut)
def create_task(
    variant_id: int,
    payload: TaskCreateIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ac.create_task(db, admin, variant_id, payload)


@router.get("/tasks/{task_id}", response_model=AdminTaskOut)
def get_task(
    task_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ac.get_task(db, task_id)


@router.patch("/tasks/{task_id}", response_model=AdminTaskOut)
def patch_task(
    task_id: int,
    payload: TaskPatchIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ac.patch_task(db, admin, task_id, payload)


@router.post("/tasks/{task_id}/archive", response_model=AdminTaskOut)
def archive_task(
    task_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ac.archive_task(db, admin, task_id)



@router.post("/tasks/{task_id}/fields", response_model=AdminFieldOut)
def create_field(
    task_id: int,
    payload: FieldCreateIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ac.create_field(db, admin, task_id, payload)


@router.patch("/fields/{field_id}", response_model=AdminFieldOut)
def patch_field(
    field_id: int,
    payload: FieldPatchIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ac.patch_field(db, admin, field_id, payload)


@router.delete("/fields/{field_id}")
def delete_field(
    field_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    deleted = ac.delete_field(db, admin, field_id)
    return {"deleted": deleted}



@router.post("/tasks/{task_id}/files", response_model=TaskFileOut)
def upload_task_file(
    task_id: int,
    file: UploadFile,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ac.upload_file(db, admin, task_id, file)


@router.delete("/files/{file_id}")
def delete_task_file(
    file_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    deleted = ac.delete_file(db, admin, file_id)
    return {"deleted": deleted}



@router.get("/settings", response_model=SettingsOut)
def get_settings_view(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return ac.get_settings_view(db)


@router.put("/settings", response_model=SettingsOut)
def update_settings(
    payload: SettingsPatchIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ac.update_settings(db, admin, payload)



@router.get("/conversion-tables", response_model=list[ConversionTableOut])
def list_conversion_tables(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return ac.list_conversion_tables(db)


@router.post("/conversion-tables", response_model=ConversionTableOut)
def create_conversion_table(
    payload: ConversionTableCreateIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ac.create_conversion_table(db, admin, payload)


@router.get("/conversion-tables/{table_id}", response_model=ConversionTableOut)
def get_conversion_table(
    table_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ac.get_conversion_table(db, table_id)


@router.patch("/conversion-tables/{table_id}", response_model=ConversionTableOut)
def patch_conversion_table(
    table_id: int,
    payload: ConversionTablePatchIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ac.patch_conversion_table(db, admin, table_id, payload)


@router.post("/conversion-tables/{table_id}/activate", response_model=ConversionTableOut)
def activate_conversion_table(
    table_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ac.activate_conversion_table(db, admin, table_id)
