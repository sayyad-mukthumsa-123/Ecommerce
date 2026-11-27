"""Version 1 catalog routes using direct parameterized SQL queries."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from ...schemas.catalog import (
    CategoryTranslationResponse,
    GeolocationResponse,
    PaginatedCategoryTranslationResponse,
    PaginatedGeolocationResponse,
    PaginatedProductResponse,
    PaginatedSellerResponse,
    ProductResponse,
    SellerResponse,
)
from ...schemas.common import PageParams, PaginationMeta
from ..deps import database_session


router = APIRouter(tags=["catalog"])
DatabaseSession = Annotated[Session, Depends(database_session)]


def _not_found(resource: str, identifier: str) -> HTTPException:
    """Build a consistent 404 response without exposing SQL details."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{resource} '{identifier}' was not found",
    )


def _pagination(
    db: Session,
    count_sql: str,
    params: dict[str, object],
    page: PageParams,
    returned: int,
) -> PaginationMeta:
    """Run a count query and create validated pagination metadata."""
    total = int(db.execute(text(count_sql), params).scalar_one() or 0)
    return PaginationMeta(total=total, limit=page.limit, offset=page.offset, returned=returned)


@router.get("/products", response_model=PaginatedProductResponse)
def list_products(
    db: DatabaseSession,
    page: Annotated[PageParams, Depends()],
    category_name: str | None = Query(default=None, min_length=1),
    category_name_english: str | None = Query(default=None, min_length=1),
) -> PaginatedProductResponse:
    """Return products with optional Portuguese or English category filters."""
    filters: list[str] = []
    params: dict[str, object] = {"limit": page.limit, "offset": page.offset}
    if category_name:
        filters.append("p.product_category_name = :category_name")
        params["category_name"] = category_name
    if category_name_english:
        filters.append("ct.product_category_name_english LIKE :category_name_english")
        params["category_name_english"] = f"%{category_name_english}%"
    where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""

    # Select only fields declared by ProductResponse so ORM/internal columns
    # never leak into the API response.
    rows = db.execute(
        text(
            f"""
            SELECT p.product_id, p.product_category_name,
                   ct.product_category_name_english,
                   p.product_name_lenght, p.product_description_lenght,
                   p.product_photos_qty, p.product_weight_g,
                   p.product_length_cm, p.product_height_cm, p.product_width_cm
            FROM products AS p
            LEFT JOIN category_translation AS ct
              ON p.product_category_name = ct.product_category_name
            {where_sql}
            ORDER BY p.product_id
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()
    items = [ProductResponse.model_validate(row) for row in rows]
    return PaginatedProductResponse(
        items=items,
        pagination=_pagination(
            db,
            f"""
            SELECT COUNT(*)
            FROM products AS p
            LEFT JOIN category_translation AS ct
              ON p.product_category_name = ct.product_category_name
            {where_sql}
            """,
            params,
            page,
            len(items),
        ),
    )


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: str, db: DatabaseSession) -> ProductResponse:
    """Return one product and its translated category name."""
    row = db.execute(
        text(
            """
            SELECT p.product_id, p.product_category_name,
                   ct.product_category_name_english,
                   p.product_name_lenght, p.product_description_lenght,
                   p.product_photos_qty, p.product_weight_g,
                   p.product_length_cm, p.product_height_cm, p.product_width_cm
            FROM products AS p
            LEFT JOIN category_translation AS ct
              ON p.product_category_name = ct.product_category_name
            WHERE p.product_id = :product_id
            """
        ),
        {"product_id": product_id},
    ).mappings().first()
    if row is None:
        raise _not_found("Product", product_id)
    return ProductResponse.model_validate(row)


@router.get("/sellers", response_model=PaginatedSellerResponse)
def list_sellers(
    db: DatabaseSession,
    page: Annotated[PageParams, Depends()],
    state: str | None = Query(default=None, min_length=2, max_length=2),
    city: str | None = Query(default=None, min_length=1),
) -> PaginatedSellerResponse:
    """Return sellers with optional state and city filters."""
    filters: list[str] = []
    params: dict[str, object] = {"limit": page.limit, "offset": page.offset}
    if state:
        filters.append("seller_state = :state")
        params["state"] = state
    if city:
        filters.append("seller_city LIKE :city")
        params["city"] = f"%{city}%"
    where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""
    rows = db.execute(
        text(
            f"""
            SELECT seller_id, seller_zip_code_prefix, seller_city, seller_state
            FROM sellers
            {where_sql}
            ORDER BY seller_id
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()
    items = [SellerResponse.model_validate(row) for row in rows]
    return PaginatedSellerResponse(
        items=items,
        pagination=_pagination(db, f"SELECT COUNT(*) FROM sellers {where_sql}", params, page, len(items)),
    )


@router.get("/sellers/{seller_id}", response_model=SellerResponse)
def get_seller(seller_id: str, db: DatabaseSession) -> SellerResponse:
    """Return one seller by seller identifier."""
    row = db.execute(
        text(
            """
            SELECT seller_id, seller_zip_code_prefix, seller_city, seller_state
            FROM sellers
            WHERE seller_id = :seller_id
            """
        ),
        {"seller_id": seller_id},
    ).mappings().first()
    if row is None:
        raise _not_found("Seller", seller_id)
    return SellerResponse.model_validate(row)


@router.get("/category-translations", response_model=PaginatedCategoryTranslationResponse)
def list_category_translations(
    db: DatabaseSession,
    page: Annotated[PageParams, Depends()],
    category_name: str | None = Query(default=None, min_length=1),
    category_name_english: str | None = Query(default=None, min_length=1),
) -> PaginatedCategoryTranslationResponse:
    """Return Portuguese-to-English category translations."""
    filters: list[str] = []
    params: dict[str, object] = {"limit": page.limit, "offset": page.offset}
    if category_name:
        filters.append("product_category_name LIKE :category_name")
        params["category_name"] = f"%{category_name}%"
    if category_name_english:
        filters.append("product_category_name_english LIKE :category_name_english")
        params["category_name_english"] = f"%{category_name_english}%"
    where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""
    rows = db.execute(
        text(
            f"""
            SELECT product_category_name, product_category_name_english
            FROM category_translation
            {where_sql}
            ORDER BY product_category_name
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()
    items = [CategoryTranslationResponse.model_validate(row) for row in rows]
    return PaginatedCategoryTranslationResponse(
        items=items,
        pagination=_pagination(
            db,
            f"SELECT COUNT(*) FROM category_translation {where_sql}",
            params,
            page,
            len(items),
        ),
    )


@router.get("/category-translations/{product_category_name}", response_model=CategoryTranslationResponse)
def get_category_translation(product_category_name: str, db: DatabaseSession) -> CategoryTranslationResponse:
    """Return one category translation by its Portuguese name."""
    row = db.execute(
        text(
            """
            SELECT product_category_name, product_category_name_english
            FROM category_translation
            WHERE product_category_name = :product_category_name
            """
        ),
        {"product_category_name": product_category_name},
    ).mappings().first()
    if row is None:
        raise _not_found("Category", product_category_name)
    return CategoryTranslationResponse.model_validate(row)


@router.get("/geolocation", response_model=PaginatedGeolocationResponse)
def list_geolocation(
    db: DatabaseSession,
    page: Annotated[PageParams, Depends()],
    state: str | None = Query(default=None, min_length=2, max_length=2),
    city: str | None = Query(default=None, min_length=1),
) -> PaginatedGeolocationResponse:
    """Return representative ZIP-prefix geolocation records."""
    filters: list[str] = []
    params: dict[str, object] = {"limit": page.limit, "offset": page.offset}
    if state:
        filters.append("geolocation_state = :state")
        params["state"] = state
    if city:
        filters.append("geolocation_city LIKE :city")
        params["city"] = f"%{city}%"
    where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""
    rows = db.execute(
        text(
            f"""
            SELECT geolocation_zip_code_prefix, geolocation_lat,
                   geolocation_lng, geolocation_city, geolocation_state
            FROM geolocation
            {where_sql}
            ORDER BY geolocation_zip_code_prefix
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()
    items = [GeolocationResponse.model_validate(row) for row in rows]
    return PaginatedGeolocationResponse(
        items=items,
        pagination=_pagination(
            db,
            f"SELECT COUNT(*) FROM geolocation {where_sql}",
            params,
            page,
            len(items),
        ),
    )


@router.get("/geolocation/{zip_code_prefix}", response_model=GeolocationResponse)
def get_geolocation(zip_code_prefix: str, db: DatabaseSession) -> GeolocationResponse:
    """Return one geolocation record by ZIP prefix."""
    row = db.execute(
        text(
            """
            SELECT geolocation_zip_code_prefix, geolocation_lat,
                   geolocation_lng, geolocation_city, geolocation_state
            FROM geolocation
            WHERE geolocation_zip_code_prefix = :zip_code_prefix
            """
        ),
        {"zip_code_prefix": zip_code_prefix},
    ).mappings().first()
    if row is None:
        raise _not_found("ZIP prefix", zip_code_prefix)
    return GeolocationResponse.model_validate(row)
