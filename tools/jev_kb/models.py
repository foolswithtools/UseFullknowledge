"""Pydantic models for KB operations — type-safe contracts for agents."""
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

class KnowledgeEntry(BaseModel):
    id: str = Field(..., description="Immutable identity: <slug>-<4hex>")
    title: str = Field(..., min_length=1)
    type: str = Field(..., pattern="^(explainer|diagram|snippet|prompt|note)$")
    summary: str = Field(..., min_length=1)
    tags: List[str] = Field(..., min_items=1)
    created_at: str
    created_by_tool: str
    created_by_model: str
    updated_at: str
    updated_by_kind: str = Field(..., pattern="^(agent|human)$")
    review_status: str = Field("unreviewed", pattern="^(unreviewed|verified|rejected)$")
    confidence_basis: List[str] = Field(default_factory=list)
    volatility: str = Field("slow", pattern="^(fast|medium|slow|glacial)$")
    sources: Optional[List[str]] = None
    review_reviewer: Optional[str] = None
    review_reviewed_at: Optional[str] = None
    review_reviewer_kind: Optional[str] = None
    body: Optional[str] = None
    path: Optional[str] = None

class SearchResult(BaseModel):
    id: str; title: str; type: str; tags: List[str]; review_status: str; path: str

class CatalogEntry(BaseModel):
    id: str; title: str; type: str; summary: str; tags: List[str]
    review_status: str; confidence_basis: List[str]; expires_on: Optional[str] = None; url: Optional[str] = None

class BatchImportResult(BaseModel):
    imported: int = 0; failed: int = 0; errors: List[str] = Field(default_factory=list); imported_ids: List[str] = Field(default_factory=list)
