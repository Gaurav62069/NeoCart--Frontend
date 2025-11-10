from sqlalchemy.orm import Session, joinedload 
from typing import List, Optional
from . import models, schemas
import firebase_admin.auth
from datetime import datetime

# --- User CRUD ---

def get_user_by_email(db: Session, email: str):
    """
    Find a user by their email address.
    Eagerly loads cart and wishlist items.
    """
    return db.query(models.User).options(
        joinedload(models.User.cart_items),
        joinedload(models.User.wishlist_items)
    ).filter(models.User.email == email).first()

def get_user_by_firebase_uid(db: Session, firebase_uid: str):
    """
    Find a user by their unique Firebase ID.
    Eagerly loads cart and wishlist items.
    """
    return db.query(models.User).options(
        joinedload(models.User.cart_items),
        joinedload(models.User.wishlist_items)
    ).filter(models.User.firebase_uid == firebase_uid).first()

def create_user_from_firebase(db: Session, firebase_user: firebase_admin.auth.UserRecord, role: str = 'retailer', business_id: Optional[str] = None, dp_url: Optional[str] = None):
    """
    Create a new user in our database after they are verified by Firebase.
    """
    is_verified = True if role == 'retailer' else False
    new_user = models.User(
        firebase_uid=firebase_user.uid,
        email=firebase_user.email,
        name=firebase_user.display_name,
        role=role,
        is_verified=is_verified,
        business_id=business_id,
        dp_url=dp_url
    )
    db.add(new_user)
    db.commit()
    # The user is re-fetched in auth.py to ensure relations are loaded
    return new_user

def update_user_profile(db: Session, user: models.User, profile_data: schemas.ProfileUpdate):
    """
    Update a user's profile information.
    Merges the detached 'user' object into the current session.
    """
    
    # Merge the detached user object into the current session
    db_user = db.merge(user)

    # Now update the merged object
    db_user.name = profile_data.name
    db_user.phone = profile_data.phone
    db_user.address = profile_data.address
    db_user.dp_url = profile_data.dp_url
    
    db.commit()
    db.refresh(db_user) 
    
    # Re-load the user with relationships to return a fresh object
    updated_user_with_relations = db.query(models.User).options(
        joinedload(models.User.cart_items),
        joinedload(models.User.wishlist_items)
    ).filter(models.User.id == db_user.id).first()
    
    return updated_user_with_relations

def get_all_users_for_admin(db: Session):
    """
    Get all users for the admin panel.
    """
    return db.query(models.User).order_by(models.User.created_at.desc()).all()

def verify_wholesaler(db: Session, user_id: int):
    """
    Mark a wholesaler as 'is_verified' by an admin.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None
    if user.role != 'wholesaler':
        return None 
        
    user.is_verified = True
    db.commit()
    db.refresh(user)
    return user


# --- Product CRUD ---

def get_products(db: Session, user_role: str, skip: int = 0, limit: int = 100, search_term: Optional[str] = None) -> List[models.Product]:
    """
    Fetch products with pagination and DYNAMIC pricing based on role.
    """
    
    query = db.query(models.Product).options(
        joinedload(models.Product.reviews) # Eager load reviews
    )

    if search_term:
        query = query.filter(models.Product.name.ilike(f"%{search_term}%"))
    
    query = query.order_by(models.Product.id).offset(skip).limit(limit)
    
    products = query.all()

    # Calculate dynamic price and discount % for each product
    for prod in products:
        if user_role == 'retailer':
            prod.discount_price = prod.retail_price
        else: # 'wholesaler'
            prod.discount_price = prod.wholesaler_price
        
        if prod.original_price > 0 and prod.discount_price < prod.original_price:
            prod.discount_percent = round(100 * (prod.original_price - prod.discount_price) / prod.original_price)
        else:
            prod.discount_percent = 0

    return products

def get_product_by_id(db: Session, product_id: int, user_role: str = 'retailer'):
    """
    Get a single product, calculating its price based on role.
    """
    product = db.query(models.Product).options(
        joinedload(models.Product.reviews).joinedload(models.Review.owner) # Eager load reviews and their owners
    ).filter(models.Product.id == product_id).first()

    if product:
        if user_role == 'retailer':
            product.discount_price = product.retail_price
        else: # 'wholesaler'
            product.discount_price = product.wholesaler_price
        
        if product.original_price > 0 and product.discount_price < product.original_price:
            product.discount_percent = round(100 * (product.original_price - product.discount_price) / product.original_price)
        else:
            product.discount_percent = 0

    return product


# --- Cart CRUD ---

def get_cart_items(db: Session, user_id: int):
    return db.query(models.CartItem).filter(models.CartItem.owner_id == user_id).all()

def add_item_to_cart(db: Session, user_id: int, item: schemas.ItemBase):
    db_item = db.query(models.CartItem).filter(
        models.CartItem.owner_id == user_id,
        models.CartItem.product_id == item.product_id
    ).first()

    if db_item:
        db_item.quantity += 1
    else:
        db_item = models.CartItem(
            **item.model_dump(),
            owner_id=user_id,
            quantity=1
        )
        db.add(db_item)
    
    db.commit()
    db.refresh(db_item)
    return db_item

def update_cart_item_quantity(db: Session, user_id: int, product_id: int, amount: int):
    db_item = db.query(models.CartItem).filter(
        models.CartItem.owner_id == user_id,
        models.CartItem.product_id == product_id
    ).first()

    if not db_item:
        return None

    db_item.quantity += amount

    if db_item.quantity <= 0:
        db.delete(db_item)
        db.commit()
        return None 
    else:
        db.commit()
        db.refresh(db_item)
        return db_item

def remove_item_from_cart(db: Session, user_id: int, product_id: int):
    db_item = db.query(models.CartItem).filter(
        models.CartItem.owner_id == user_id,
        models.CartItem.product_id == product_id
    ).first()

    if db_item:
        db.delete(db_item)
        db.commit()
        return True
    return False

def clear_user_cart(db: Session, user_id: int):
    db.query(models.CartItem).filter(models.CartItem.owner_id == user_id).delete()
    db.commit()
    return True

# --- Wishlist CRUD ---

def get_wishlist_items(db: Session, user_id: int):
    return db.query(models.WishlistItem).filter(models.WishlistItem.owner_id == user_id).all()

def add_item_to_wishlist(db: Session, user_id: int, item: schemas.ItemBase):
    db_item = db.query(models.WishlistItem).filter(
        models.WishlistItem.owner_id == user_id,
        models.WishlistItem.product_id == item.product_id
    ).first()

    if db_item:
        return db_item
    
    db_item = models.WishlistItem(
        **item.model_dump(),
        owner_id=user_id
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def remove_item_from_wishlist(db: Session, user_id: int, product_id: int):
    db_item = db.query(models.WishlistItem).filter(
        models.WishlistItem.owner_id == user_id,
        models.WishlistItem.product_id == product_id
    ).first()

    if db_item:
        db.delete(db_item)
        db.commit()
        return True
    return False

# --- Coupon CRUD ---

def get_coupon_by_code(db: Session, code: str):
    today = datetime.now().date()
    return db.query(models.Coupon).filter(
        models.Coupon.code == code,
        models.Coupon.is_active == True,
        models.Coupon.expires_at >= today
    ).first()

# --- Order CRUD ---

def get_orders_by_user(db: Session, user_id: int):
    """
    Get all orders for a user.
    Eager load order items and shipping address.
    """
    return db.query(models.Order).options(
        joinedload(models.Order.order_items),
        joinedload(models.Order.shipping_address)
    ).filter(models.Order.owner_id == user_id).order_by(models.Order.created_at.desc()).all()

def create_order(db: Session, user_id: int, order_data: schemas.OrderCreate):
    shipping_details = order_data.shipping_details
    db_address = models.ShippingAddress(
        name=shipping_details.name,
        email=shipping_details.email,
        phone=shipping_details.phone,
        address=shipping_details.address,
        city=shipping_details.city,
        pincode=shipping_details.pincode
    )
    db.add(db_address)
    db.commit()
    db.refresh(db_address)

    db_order = models.Order(
        owner_id=user_id,
        total_price=order_data.total_price,
        shipping_address_id=db_address.id
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    for item_data in order_data.order_items:
        db_order_item = models.OrderItem(
            order_id=db_order.id,
            product_id=item_data.product_id,
            product_name=item_data.product_name,
            quantity=item_data.quantity,
            price=item_data.price,
            image_url=item_data.image_url
        )
        db.add(db_order_item)
    
    db.commit()
    
    db.refresh(db_order)
    return db_order

# --- Review CRUD ---

def get_reviews_for_product(db: Session, product_id: int):
    """
    Get all reviews for a product.
    Eager load the owner of the review.
    """
    return db.query(models.Review).options(
        joinedload(models.Review.owner)
    ).filter(models.Review.product_id == product_id).order_by(models.Review.created_at.desc()).all()

def create_review(db: Session, user_id: int, review_data: schemas.ReviewCreate):
    db_review = models.Review(
        **review_data.model_dump(),
        owner_id=user_id
    )
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    
    # Re-fetch the review with the owner loaded
    db_review_with_owner = db.query(models.Review).options(
        joinedload(models.Review.owner)
    ).filter(models.Review.id == db_review.id).first()
    
    return db_review_with_owner