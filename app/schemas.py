from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EntitySpan(BaseModel):
    text: str
    label: str
    start: int
    end: int
    score: float = 1.0


class NERRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000,
                      description="News / Wikipedia text to analyse")
    labels: Optional[List[str]] = Field(
        default=None,
        description="Override labels (default: PERSON, GPE, ORG, EVENT, DATE)")
    threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class NERResponse(BaseModel):
    entities: List[EntitySpan]
    grouped: Dict[str, List[str]]
    counts: Dict[str, int]
    total: int
    inference_ms: float
    model: Dict[str, str]


class SampleOut(BaseModel):
    id: str
    title: str
    source: str
    text: str


class AboutOut(BaseModel):
    project: str
    description: str
    author: str
    role: str
    portfolio: str
    github: str
