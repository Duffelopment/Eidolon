"""Pydantic schemas for API serialization."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class FindingBase(BaseModel):
    name: str
    category: Optional[str] = None
    severity: str
    description: Optional[str] = None


class Finding(FindingBase):
    id: int

    class Config:
        orm_mode = True


class ScanBase(BaseModel):
    filename: str
    size: int
    md5: str
    sha1: str
    sha256: str
    mime_type: Optional[str]
    score: int
    summary: Optional[str]


class Scan(ScanBase):
    id: int
    created_at: datetime
    findings: List[Finding] = Field(default_factory=list)

    class Config:
        orm_mode = True


class ApiEndpointBase(BaseModel):
    name: str
    base_url: str
    auth_type: Optional[str] = None
    api_key: Optional[str] = None
    headers_json: Optional[str] = None
    notes: Optional[str] = None


class ApiEndpoint(ApiEndpointBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    last_tested_at: Optional[datetime]
    last_test_status: Optional[str]
    last_test_notes: Optional[str]

    class Config:
        orm_mode = True


class ApiEndpointUpdate(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    auth_type: Optional[str] = None
    api_key: Optional[str] = None
    headers_json: Optional[str] = None
    notes: Optional[str] = None


class GraphNode(BaseModel):
    id: str
    label: str
    type: str


class GraphLink(BaseModel):
    source: str
    target: str
    label: Optional[str] = None


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    links: List[GraphLink]
