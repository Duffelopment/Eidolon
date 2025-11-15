"""Database helper functions."""
from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Optional

from sqlalchemy.orm import Session

from . import models, schemas


def create_scan(
    db: Session,
    *,
    filename: str,
    size: int,
    md5: str,
    sha1: str,
    sha256: str,
    mime_type: Optional[str],
    score: int,
    summary: Optional[str],
    findings: Iterable[schemas.FindingBase],
) -> models.Scan:
    scan = models.Scan(
        filename=filename,
        size=size,
        md5=md5,
        sha1=sha1,
        sha256=sha256,
        mime_type=mime_type,
        score=score,
        summary=summary,
    )
    for finding in findings:
        scan.findings.append(
            models.Finding(
                name=finding.name,
                category=finding.category,
                severity=finding.severity,
                description=finding.description,
            )
        )

    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


def list_scans(db: Session) -> List[models.Scan]:
    return db.query(models.Scan).order_by(models.Scan.created_at.desc()).all()


def get_scan(db: Session, scan_id: int) -> Optional[models.Scan]:
    return db.query(models.Scan).filter(models.Scan.id == scan_id).first()


def delete_scan(db: Session, scan_id: int) -> None:
    scan = get_scan(db, scan_id)
    if scan:
        db.delete(scan)
        db.commit()


def create_api_endpoint(db: Session, endpoint: schemas.ApiEndpointBase) -> models.ApiEndpoint:
    api = models.ApiEndpoint(**endpoint.dict())
    db.add(api)
    db.commit()
    db.refresh(api)
    return api


def list_api_endpoints(db: Session) -> List[models.ApiEndpoint]:
    return db.query(models.ApiEndpoint).order_by(models.ApiEndpoint.created_at.desc()).all()


def get_api_endpoint(db: Session, endpoint_id: int) -> Optional[models.ApiEndpoint]:
    return db.query(models.ApiEndpoint).filter(models.ApiEndpoint.id == endpoint_id).first()


def update_api_endpoint(
    db: Session, endpoint_id: int, payload: schemas.ApiEndpointUpdate
) -> Optional[models.ApiEndpoint]:
    api = get_api_endpoint(db, endpoint_id)
    if not api:
        return None

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(api, field, value)

    api.updated_at = datetime.utcnow()
    db.add(api)
    db.commit()
    db.refresh(api)
    return api


def delete_api_endpoint(db: Session, endpoint_id: int) -> bool:
    api = get_api_endpoint(db, endpoint_id)
    if not api:
        return False
    db.delete(api)
    db.commit()
    return True


def record_api_test(
    db: Session, endpoint_id: int, status: str, notes: Optional[str]
) -> Optional[models.ApiEndpoint]:
    api = get_api_endpoint(db, endpoint_id)
    if not api:
        return None
    api.last_tested_at = datetime.utcnow()
    api.last_test_status = status
    api.last_test_notes = notes
    api.updated_at = datetime.utcnow()
    db.add(api)
    db.commit()
    db.refresh(api)
    return api
