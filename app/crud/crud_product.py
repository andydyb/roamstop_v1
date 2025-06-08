from sqlalchemy.orm import Session
from typing import Optional, List

from app.models.product import ProductPackage
from app.schemas.product import ProductPackageCreate, ProductPackageUpdate

def get_product(db: Session, product_id: int, *, show_inactive: bool = False) -> Optional[ProductPackage]:
    """
    Get a single product package by ID.
    By default, only active products are returned unless show_inactive is True.
    """
    query = db.query(ProductPackage).filter(ProductPackage.id == product_id)
    if not show_inactive:
        query = query.filter(ProductPackage.is_active == True)
    result = query.first()
    print(f"[CRUD get_product] ID: {product_id}, show_inactive: {show_inactive}, Found: {'Yes' if result else 'No'}, Active in DB: {result.is_active if result else 'N/A'}")
    return result

def get_products_by_country(
    db: Session, *, country_code: str, is_active: bool = True, skip: int = 0, limit: int = 100
) -> List[ProductPackage]:
    """
    Get product packages by country code.
    By default, only active products are returned.
    """
    query = db.query(ProductPackage).filter(ProductPackage.country_code == country_code.upper())
    if is_active:
        query = query.filter(ProductPackage.is_active == True)
    return query.order_by(ProductPackage.name).offset(skip).limit(limit).all()

def get_all_products(
    db: Session, *, is_active: Optional[bool] = None, skip: int = 0, limit: int = 100
) -> List[ProductPackage]:
    """
    Get all product packages.
    Can filter by active status. If is_active is None, returns all.
    """
    query = db.query(ProductPackage)
    if is_active is not None:
        query = query.filter(ProductPackage.is_active == is_active)
    return query.order_by(ProductPackage.name).offset(skip).limit(limit).all()

def create_product(db: Session, *, obj_in: ProductPackageCreate) -> ProductPackage:
    """
    Create a new product package.
    """
    # Pydantic V2 uses model_dump()
    db_obj = ProductPackage(**obj_in.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def update_product(
    db: Session, *, db_obj: ProductPackage, obj_in: ProductPackageUpdate
) -> ProductPackage:
    """
    Update an existing product package.
    """
    # Pydantic V2 uses model_dump(exclude_unset=True) for partial updates
    update_data = obj_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_obj, field, value)

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def delete_product(db: Session, *, product_id: int) -> Optional[ProductPackage]:
    """
    Logically delete a product package by setting its is_active flag to False.
    Returns the "deleted" product package object if found, otherwise None.
    """
    db_obj = db.query(ProductPackage).filter(ProductPackage.id == product_id).first()
    if db_obj:
        if db_obj.is_active: # Only "delete" if it's currently active
            db_obj.is_active = False
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
        return db_obj # Return object whether it was active or already inactive
    return None # Product not found

def hard_delete_product(db: Session, *, product_id: int) -> Optional[ProductPackage]:
    """
    Permanently delete a product package from the database.
    Returns the deleted product package object if found and deleted, otherwise None.
    USE WITH CAUTION.
    """
    db_obj = db.query(ProductPackage).filter(ProductPackage.id == product_id).first()
    if db_obj:
        db.delete(db_obj)
        db.commit()
        return db_obj
    return None

def get_distinct_active_countries(db: Session) -> List[str]:
    """
    Get a list of distinct country codes from active product packages, ordered alphabetically.
    """
    query = db.query(ProductPackage.country_code)\
              .filter(ProductPackage.is_active == True)\
              .distinct()\
              .order_by(ProductPackage.country_code)
    return [row[0] for row in query.all()]
