import pandas as pd
import requests
from io import BytesIO
import threading
from .database import SessionLocal
from .models import Product

# ✅ Correct Google Sheets export link
EXCEL_URL = "https://docs.google.com/spreadsheets/d/1J4OprDdBPhB3M8_xmKob6vV5WXLkON3L/export?format=xlsx"

update_lock = threading.Lock()

def run_seeding():
    """Fetch Excel from Google Drive & sync with database."""
    if not update_lock.acquire(blocking=False):
        print("⚙️ Update already running. Skipping.")
        return

    print("📥 Fetching Excel data from Google Sheets...")
    db = SessionLocal()

    try:
        response = requests.get(EXCEL_URL)
        if response.status_code != 200:
            print(f"❌ Failed to fetch sheet (status {response.status_code})")
            return

        # Load into DataFrame
        df = pd.read_excel(BytesIO(response.content))
        df = df.fillna('')

        added, updated = 0, 0

        for _, row in df.iterrows():
            existing = db.query(Product).filter(Product.name == row['name']).first()
            if existing:
                existing.description = row['description']
                existing.original_price = float(row['original_price'])
                existing.image_url = row['image_url']
                existing.stock = int(row['stock'])
                existing.retail_price = float(row['retail_price'])
                existing.wholesaler_price = float(row['wholesaler_price'])
                updated += 1
            else:
                new_product = Product(
                    name=row['name'],
                    description=row['description'],
                    original_price=float(row['original_price']),
                    image_url=row['image_url'],
                    stock=int(row['stock']),
                    retail_price=float(row['retail_price']),
                    wholesaler_price=float(row['wholesaler_price'])
                )
                db.add(new_product)
                added += 1

        db.commit()
        print(f"✅ Sync complete! {added} added, {updated} updated.")

    except Exception as e:
        db.rollback()
        print(f"⚠️ Error during sync: {e}")
    finally:
        db.close()
        update_lock.release()
