"""Routes responsible for file scanning."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db
from ..services.scanner import analyze_file, build_graph_payload

router = APIRouter(prefix="/api/scans", tags=["scans"])


@router.get("", response_model=list[schemas.Scan])
def list_scans(db: Session = Depends(get_db)):
    """Return all stored scans, newest first."""
    scans = crud.list_scans(db)
    return [schemas.Scan.from_orm(scan) for scan in scans]


@router.get("/{scan_id}", response_model=schemas.Scan)
def get_scan(scan_id: int, db: Session = Depends(get_db)):
    scan = crud.get_scan(db, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return schemas.Scan.from_orm(scan)


@router.delete("/{scan_id}", status_code=204)
def delete_scan(scan_id: int, db: Session = Depends(get_db)):
    crud.delete_scan(db, scan_id)


@router.post("", response_model=schemas.Scan, status_code=201)
async def upload_scan(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty files cannot be scanned")

    scan_schema, finding_schemas = analyze_file(file_bytes, file.filename)

    scan = crud.create_scan(
        db,
        filename=scan_schema.filename,
        size=scan_schema.size,
        md5=scan_schema.md5,
        sha1=scan_schema.sha1,
        sha256=scan_schema.sha256,
        mime_type=scan_schema.mime_type,
        score=scan_schema.score,
        summary=scan_schema.summary,
        findings=finding_schemas,
    )
    return schemas.Scan.from_orm(scan)


@router.get("/{scan_id}/graph", response_model=schemas.GraphResponse)
def get_graph(scan_id: int, db: Session = Depends(get_db)):
    scan = crud.get_scan(db, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    graph = build_graph_payload(schemas.Scan.from_orm(scan), [schemas.Finding.from_orm(f) for f in scan.findings])
    return graph
