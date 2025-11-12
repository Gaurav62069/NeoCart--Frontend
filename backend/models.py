from sqlalchemy import Boolean, Column, Integer, String, Float, ForeignKey, DateTime, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    firebase_uid = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    dp_url = Column(String, nullable=True)
    
    role = Column(String, default="retailer")
    is_verified = Column(Boolean, default=False)
    business_id = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    cart_items = relationship("CartItem", back_populates="owner", cascade="all, delete-orphan")
    wishlist_items = relationship("WishlistItem", back_populates="owner", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="owner")
    reviews = relationship("Review", back_populates="owner")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    
    original_price = Column(Float, nullable=False)
    
    # Updated to match the Excel file structure
    retail_price = Column(Float, nullable=False, default=0.0)
    wholesaler_price = Column(Float, nullable=False, default=0.0)
    
    image_url = Column(String, nullable=False)
    stock = Column(Integer, default=0)
    
    # Relationships
    reviews = relationship("Review", back_populates="product")

class CartItem(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, nullable=False)
    
    product_name = Column(String)
    price = Column(Float)
    image_url = Column(String)
    quantity = Column(Integer, default=1)
    
    # Relationships
    owner = relationship("User", back_populates="cart_items")

class WishlistItem(Base):
    __tablename__ = "wishlist_items"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, nullable=False)
    
    product_name = Column(String)
    price = Column(Float)
    image_url = Column(String)
    
    # Relationships
    owner = relationship("User", back_populates="wishlist_items")

class Coupon(Base):
    __tablename__ = "coupons"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    discount_percent = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    expires_at = Column(Date, nullable=True)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_price = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    shipping_address_id = Column(Integer, ForeignKey("shipping_addresses.id"), nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    shipping_address = relationship("ShippingAddress")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, nullable=False)
    
    product_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    image_url = Column(String, nullable=False)
    
    # Relationships
    order = relationship("Order", back_populates="order_items")

class ShippingAddress(Base):
    __tablename__ = "shipping_addresses"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    address = Column(String, nullable=False)
    city = Column(String, nullable=False)
    pincode = Column(String, nullable=False)

class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    rating = Column(Integer, nullable=False)
    comment = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="reviews")
    product = relationship("Product", back_populates="reviews")