"""Routes for managing external API calibrations."""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/api/apis", tags=["apis"])


@router.get("", response_model=list[schemas.ApiEndpoint])
def list_api_endpoints(db: Session = Depends(get_db)):
    return [schemas.ApiEndpoint.from_orm(api) for api in crud.list_api_endpoints(db)]


@router.post("", response_model=schemas.ApiEndpoint, status_code=201)
def create_api_endpoint(endpoint: schemas.ApiEndpointBase, db: Session = Depends(get_db)):
    api = crud.create_api_endpoint(db, endpoint)
    return schemas.ApiEndpoint.from_orm(api)


@router.put("/{endpoint_id}", response_model=schemas.ApiEndpoint)
def update_api_endpoint(
    endpoint_id: int, payload: schemas.ApiEndpointUpdate, db: Session = Depends(get_db)
):
    api = crud.update_api_endpoint(db, endpoint_id, payload)
    if not api:
        raise HTTPException(status_code=404, detail="API endpoint not found")
    return schemas.ApiEndpoint.from_orm(api)


@router.delete("/{endpoint_id}", status_code=204)
def delete_api_endpoint(endpoint_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_api_endpoint(db, endpoint_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="API endpoint not found")


@router.post("/{endpoint_id}/calibrate", response_model=schemas.ApiEndpoint)
def calibrate_api_endpoint(
    endpoint_id: int,
    payload: dict | None = Body(default=None),
    db: Session = Depends(get_db),
):
    """Simulate hitting an endpoint and persist the calibration notes."""
    api = crud.get_api_endpoint(db, endpoint_id)
    if not api:
        raise HTTPException(status_code=404, detail="API endpoint not found")

    notes = "Calibration executed without network call."
    request_template = None
    if payload and isinstance(payload, dict):
        request_template = payload.get("request_template")

    if request_template:
        notes += f" Template stored: {request_template!r}"

    api = crud.record_api_test(db, endpoint_id, status="calibrated", notes=notes)
    return schemas.ApiEndpoint.from_orm(api)
