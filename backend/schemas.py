from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime, date

# --- Item Schemas (Cart & Wishlist) ---
class ItemBase(BaseModel):
    product_id: int
    product_name: str
    price: float
    image_url: str

class CartItem(ItemBase):
    id: int
    owner_id: int
    quantity: int

    model_config = ConfigDict(from_attributes=True)

class WishlistItem(ItemBase):
    id: int
    owner_id: int

    model_config = ConfigDict(from_attributes=True)

# --- Review Schemas ---
class ReviewOwner(BaseModel):
    name: Optional[str] = None
    email: str
    dp_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ReviewBase(BaseModel):
    product_id: int
    rating: int
    comment: Optional[str] = None

class ReviewCreate(ReviewBase):
    pass

class Review(ReviewBase):
    id: int
    owner_id: int
    created_at: datetime
    owner: ReviewOwner 

    model_config = ConfigDict(from_attributes=True)

# --- User Schemas ---
class UserBase(BaseModel):
    id: int # <-- This ID is needed for the AdminPage
    email: str
    name: Optional[str] = None
    role: str
    is_verified: bool
    business_id: Optional[str] = None
    dp_url: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class User(UserBase):
    cart_items: List[CartItem] = []
    wishlist_items: List[WishlistItem] = []

class UserWithToken(User):
    access_token: str

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    dp_url: Optional[str] = None

class FirebaseLoginRequest(BaseModel):
    token: str
    role: Optional[str] = 'retailer'
    business_id: Optional[str] = None
    dp_url: Optional[str] = None

# --- Auth Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# --- YAHAN NAYA SCHEMA ADD KIYA GAYA HAI ---
# --- Product Schema ---

class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    original_price: float
    retail_price: float
    wholesaler_price: float
    image_url: str
    stock: int

class Product(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    original_price: float
    
    # These fields are added dynamically in crud.py
    discount_price: float = 0.0 
    discount_percent: float = 0.0
    
    # These fields come from the database (models.py)
    retail_price: float
    wholesaler_price: float
    
    image_url: str
    stock: int
    reviews: List[Review] = [] 

    model_config = ConfigDict(from_attributes=True)

class ProductListAdmin(BaseModel):
    products: List[Product]
    total_count: int
# --- Coupon Schemas ---
class CouponApply(BaseModel):
    code: str

class Coupon(BaseModel):
    id: int
    code: str
    discount_percent: float
    is_active: bool
    expires_at: date

    model_config = ConfigDict(from_attributes=True)

# --- Order & Checkout Schemas ---
class ShippingAddressBase(BaseModel):
    name: str
    email: str
    phone: str
    address: str
    city: str
    pincode: str

class ShippingAddress(ShippingAddressBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class OrderItemBase(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    price: float
    image_url: str

class OrderItem(OrderItemBase):
    id: int
    order_id: int

    model_config = ConfigDict(from_attributes=True)

class OrderBase(BaseModel):
    total_price: float
    created_at: datetime
    shipping_address: ShippingAddress
    order_items: List[OrderItem] = []

class OrderCreate(BaseModel):
    shipping_details: ShippingAddressBase
    order_items: List[OrderItemBase]
    total_price: float

class Order(OrderBase):
    id: int
    owner_id: int

    model_config = ConfigDict(from_attributes=True)