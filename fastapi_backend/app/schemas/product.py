from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=255,
    )

    description: Optional[str] = None

    category: str = Field(
        default="general",
        min_length=2,
        max_length=100,
    )

    price: Decimal = Field(
        ...,
        gt=0,
    )

    stock: int = Field(
        ...,
        ge=0,
    )

    images: List[str] = Field(
        default_factory=list,
    )

    popularity: int = Field(
        default=0,
        ge=0,
    )


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=255,
    )

    description: Optional[str] = None

    category: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    price: Optional[Decimal] = Field(
        default=None,
        gt=0,
    )

    stock: Optional[int] = Field(
        default=None,
        ge=0,
    )

    images: Optional[List[str]] = None

    popularity: Optional[int] = Field(
        default=None,
        ge=0,
    )


class ProductResponse(BaseModel):
    id: str

    name: str

    description: Optional[str]

    category: str

    price: Decimal

    stock: int

    images: List[str]

    popularity: int

    created_at: datetime

    updated_at: datetime

    class Config:
        from_attributes = True
