from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

# Local modules
from . import crud, models, schemas, auth
from .database import get_db # Import get_db from database.py

# Ek naya router banaya
router = APIRouter()

# === Products API ===
@router.get("/products", response_model=List[schemas.Product])
def read_products(
    user_role: str = Query(..., enum=["retailer", "wholesaler"]),
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    products = crud.get_products(
        db=db, 
        user_role=user_role, 
        skip=skip, 
        limit=limit, 
        search_term=search
    )
    return products

@router.get("/products/{product_id}", response_model=schemas.Product)
def read_product(
    product_id: int, 
    user_role: str = Query("retailer", enum=["retailer", "wholesaler"]), 
    db: Session = Depends(get_db)
):
    db_product = crud.get_product_by_id(db, product_id=product_id, user_role=user_role)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

# === Users API ===
@router.get("/users/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(auth.get_current_active_user)):
    return current_user

@router.put("/users/me", response_model=schemas.UserWithToken)
def update_user_profile(
    profile_data: schemas.ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    updated_user = crud.update_user_profile(db, user=current_user, profile_data=profile_data)
    access_token = auth.create_access_token(
        data={
            "sub": updated_user.email,
            "role": updated_user.role,
            "is_verified": updated_user.is_verified,
            "dp_url": updated_user.dp_url
        }
    )
    setattr(updated_user, 'access_token', access_token)
    return updated_user

# === Cart API ===
@router.post("/cart/add", response_model=schemas.CartItem)
def add_to_cart(
    item: schemas.ItemBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    return crud.add_item_to_cart(db=db, user_id=current_user.id, item=item)

@router.post("/cart/update", response_model=Optional[schemas.CartItem])
def update_cart_quantity(
    product_id: int,
    amount: int = Query(..., description="Amount to add (e.g., 1 or -1)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    return crud.update_cart_item_quantity(db=db, user_id=current_user.id, product_id=product_id, amount=amount)

@router.delete("/cart/remove/{product_id}", status_code=204)
def remove_from_cart(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    success = crud.remove_item_from_cart(db=db, user_id=current_user.id, product_id=product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Item not found in cart")
    return {"ok": True}

@router.post("/cart/apply-coupon", response_model=schemas.Coupon)
def apply_coupon(
    coupon_data: schemas.CouponApply,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    coupon = crud.get_coupon_by_code(db, code=coupon_data.code)
    if not coupon:
        raise HTTPException(status_code=404, detail="Invalid or expired coupon code")
    return coupon

# === Wishlist API ===
@router.post("/wishlist/add", response_model=schemas.WishlistItem)
def add_to_wishlist(
    item: schemas.ItemBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    return crud.add_item_to_wishlist(db=db, user_id=current_user.id, item=item)

@router.delete("/wishlist/remove/{product_id}", status_code=204)
def remove_from_wishlist(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    success = crud.remove_item_from_wishlist(db=db, user_id=current_user.id, product_id=product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Item not found in wishlist")
    return {"ok": True}

# === Order API ===
@router.post("/orders/checkout", response_model=schemas.Order)
def checkout(
    order_data: schemas.OrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    order = crud.create_order(db=db, user_id=current_user.id, order_data=order_data)
    crud.clear_user_cart(db=db, user_id=current_user.id)
    return order

@router.get("/orders/me", response_model=List[schemas.Order])
def get_my_orders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    return crud.get_orders_by_user(db=db, user_id=current_user.id)

# === Reviews API ===
@router.get("/reviews/{product_id}", response_model=List[schemas.Review])
def get_product_reviews(product_id: int, db: Session = Depends(get_db)):
    return crud.get_reviews_for_product(db=db, product_id=product_id)

@router.post("/reviews", response_model=schemas.Review)
def create_review(
    review_data: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    product = crud.get_product_by_id(db, product_id=review_data.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return crud.create_review(db=db, user_id=current_user.id, review_data=review_data)

# === Admin API ===
@router.get("/admin/users", response_model=List[schemas.UserBase])
def admin_get_all_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    return crud.get_all_users_for_admin(db)

@router.post("/admin/verify/{user_id}", response_model=schemas.UserBase)
def admin_verify_wholesaler(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    user = crud.verify_wholesaler(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Wholesaler user not found or user is not a wholesaler")
    return user