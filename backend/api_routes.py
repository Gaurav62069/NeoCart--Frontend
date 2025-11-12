from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import pandas as pd
import io
from fastapi.responses import StreamingResponse # Download Excel ke liye

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

# === Admin Product Management ===

@router.post("/admin/products", response_model=schemas.Product)
def admin_create_product(
    product_data: schemas.ProductCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    """
    Feature 1: Admin ke liye naya product manually add karna.
    """
    return crud.create_product(db=db, product_data=product_data)


@router.post("/admin/upload-excel")
async def admin_upload_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    """
    Feature 2: Admin ke liye Excel se bulk product upload/update karna.
    """
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents), engine='openpyxl')
        df = df.fillna('') 
        
        products_added = 0
        products_updated = 0
        
        for index, row in df.iterrows():
            existing_product = db.query(models.Product).filter(models.Product.name == row['name']).first()

            if existing_product:
                existing_product.description = row['description']
                existing_product.original_price = float(row['original_price'])
                existing_product.image_url = row['image_url']
                existing_product.stock = int(row['stock'])
                existing_product.retail_price = float(row['retail_price'])
                existing_product.wholesaler_price = float(row['wholesaler_price'])
                products_updated += 1
            else:
                new_product = models.Product(
                    name=row['name'],
                    description=row['description'],
                    original_price=float(row['original_price']),
                    image_url=row['image_url'],
                    stock=int(row['stock']),
                    retail_price = float(row['retail_price']),
                    wholesaler_price = float(row['wholesaler_price'])
                )
                db.add(new_product)
                products_added += 1
        
        db.commit()
        return {
            "status": "success",
            "added": products_added,
            "updated": products_updated
        }
        
    except Exception as e:
        db.rollback() 
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@router.put("/admin/products/{product_id}", response_model=schemas.Product)
def admin_update_product(
    product_id: int,
    product_data: schemas.ProductCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    """
    Feature 3: Admin ke liye ek product ko update karna.
    """
    updated_product = crud.update_product(db=db, product_id=product_id, product_data=product_data)
    if updated_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return updated_product


@router.delete("/admin/products/{product_id}", response_model=schemas.Product)
def admin_delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    """
    Feature 4: Admin ke liye ek single product ko delete karna.
    """
    deleted_product = crud.delete_product(db=db, product_id=product_id)
    if deleted_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return deleted_product


@router.delete("/admin/products-all")
def admin_delete_all_products(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    """
    Feature 5: Admin ke liye saare products ko delete karna (DANGEROUS).
    """
    rows_deleted = crud.delete_all_products(db=db)
    return {"status": "success", "products_deleted": rows_deleted}


@router.get("/admin/products/download-excel")
async def admin_download_excel(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    """
    Feature 6: Admin ke liye saare products ko Excel file mein download karna.
    """
    try:
        products = crud.get_all_products_for_excel(db)
        
        products_dict = [
            {
                "name": p.name,
                "description": p.description,
                "original_price": p.original_price,
                "retail_price": p.retail_price,
                "wholesaler_price": p.wholesaler_price,
                "image_url": p.image_url,
                "stock": p.stock
            }
            for p in products
        ]
        
        df = pd.DataFrame(products_dict)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Products', index=False)
        
        output.seek(0) 
        
        headers = {
            'Content-Disposition': 'attachment; filename="all_products.xlsx"'
        }
        
        return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate Excel file: {str(e)}")


@router.get("/admin/products-list", response_model=schemas.ProductListAdmin)
def admin_get_products_list_paginated(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    """
    Feature 7: Admin ke liye paginated product list fetch karna.
    """
    products = crud.get_products_for_admin_paginated(db, skip=skip, limit=limit)
    total_count = crud.get_products_count(db)
    return {"products": products, "total_count": total_count}