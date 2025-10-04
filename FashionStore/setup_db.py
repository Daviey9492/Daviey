import sqlite3

DB = "fashion_store.db"

def setup_database():
    """Create the Inventory table and insert sample items."""
    try:
        with sqlite3.connect(DB) as conn:
            cur = conn.cursor()
            print(f"→ Connected to {DB}")

            cur.execute("""
                CREATE TABLE IF NOT EXISTS Inventory (
                    id INTEGER PRIMARY KEY,
                    item_name TEXT NOT NULL,
                    unit_price REAL NOT NULL,
                    color TEXT,
                    description TEXT,
                    image TEXT,
                    qty_initial_bought INTEGER DEFAULT 0,
                    qty_sold INTEGER DEFAULT 0
                );
            """)
            print("→ Table 'Inventory' ready.")

            # --- 13 Sample Items ---
            items = [
                # Dresses
                (101, 'Crimson Red Evening Gown', 5500, 'Crimson Red', 'Full-length silky gown, perfect for formal events.', 'placeholder_dress_1.jpg', 15),
                (102, 'Flowy Floral Summer Maxi', 3500, 'Floral Print', 'Light cotton maxi with straps, great for sunny days.', 'placeholder_dress_2.jpg', 25),
                (103, 'Little Black Dress', 2700, 'Black', 'Classic A-line black dress, versatile wear.', 'placeholder_dress_3.jpg', 30),
                (104, 'Sequin Cocktail Dress', 4300, 'Silver', 'Sparkly sequin cocktail dress for parties.', 'placeholder_dress_4.jpg', 10),

                # Outerwear
                (201, 'Classic Trench Coat', 5800, 'Beige', 'Water-resistant trench with belt, timeless style.', 'placeholder_coat_1.jpg', 20),
                (202, 'Vintage Denim Jacket', 2000, 'Dark Wash Blue', 'Relaxed-fit timeless denim jacket.', 'placeholder_jacket_1.jpg', 25),
                (203, 'Plaid Wool Blazer', 5600, 'Grey Plaid', 'Structured wool blazer for office and casual wear.', 'placeholder_blazer_1.jpg', 18),

                # Accessories
                (301, 'Designer Leather Tote', 2500, 'Brown', 'Large leather tote with gold accents.', 'placeholder_bag_1.jpg', 18),
                (302, 'Hand-Printed Silk Scarf', 1500, 'Various', '100% silk scarf with hand-rolled edges.', 'placeholder_scarf_1.jpg', 40),
                (303, 'Layered Gold Necklace', 4000, 'Gold', 'Delicate adjustable layered necklace.', 'placeholder_necklace_1.jpg', 35),
                (304, 'Premium Leather Belt', 4500, 'Various', 'Genuine leather belt with steel buckle.', 'placeholder_belt_1.jpg', 30),

                # Shoes
                (401, 'Stiletto High Heels', 3000, 'Black Suede', 'Elegant 4-inch stiletto heels.', 'placeholder_shoe_1.jpg', 22),
                (402, 'Urban Canvas Sneakers', 2300, 'White', 'Light and comfy sneakers for everyday wear.', 'placeholder_shoe_2.jpg', 28),
            ]

            cur.executemany("""
                INSERT OR IGNORE INTO Inventory 
                (id, item_name, unit_price, color, description, image, qty_initial_bought, qty_sold)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """, items)

            conn.commit()
            print(f"✅ Database setup complete. {len(items)} items inserted or verified.")

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    setup_database()
