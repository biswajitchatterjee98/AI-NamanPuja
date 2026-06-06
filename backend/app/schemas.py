from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class BatchStatus(str, Enum):
    PENDING = "PENDING"
    GENERATING = "GENERATING"
    QC_COMPLETE = "QC_COMPLETE"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    UPLOADED = "UPLOADED"


class PageInput(BaseModel):
    puja: str = Field(..., min_length=1, max_length=200)
    city: str = Field(..., min_length=1, max_length=200)
    state: str = Field(..., min_length=1, max_length=200)
    country: str = Field(..., min_length=1, max_length=200)


class SeoMetadata(BaseModel):
    title: str
    description: str
    keywords: list[str] = Field(default_factory=list)


class FaqItem(BaseModel):
    question: str
    answer: str


class ImageAsset(BaseModel):
    path: str
    caption: str = ""
    alt: str = ""


class QcResult(BaseModel):
    passed: bool
    issues: list[str] = Field(default_factory=list)


class PageDocument(BaseModel):
    id: str | None = None
    batch_id: str
    puja: str
    city: str
    state: str
    country: str
    slug: str = ""
    content: str = ""
    faq: list[FaqItem] = Field(default_factory=list)
    seo: SeoMetadata | None = None
    images: list[ImageAsset] = Field(default_factory=list)
    qc: QcResult | None = None
    upload_status: str | None = None
    generated_at: datetime | None = None


class BatchDocument(BaseModel):
    id: str | None = None
    status: BatchStatus = BatchStatus.PENDING
    created_at: datetime
    updated_at: datetime
    page_inputs: list[PageInput] = Field(default_factory=list)
    parent_batch_id: str | None = None
    prompt_version: str = "v1"
    generation_metadata: dict[str, Any] = Field(default_factory=dict)


class FeedbackDocument(BaseModel):
    id: str | None = None
    batch_id: str
    decision: str
    comments: str
    timestamp: datetime


class BatchCreateRequest(BaseModel):
    pages: list[PageInput] = Field(..., min_length=1, max_length=50)
    parent_batch_id: str | None = None


class BatchRejectRequest(BaseModel):
    comments: str = Field(..., min_length=1, max_length=5000)


class BatchSummary(BaseModel):
    id: str
    status: BatchStatus
    created_at: datetime
    updated_at: datetime
    page_count: int
    parent_batch_id: str | None = None


class BatchDetailResponse(BaseModel):
    batch: BatchDocument
    pages: list[PageDocument]


class HealthResponse(BaseModel):
    status: str
    service: str
