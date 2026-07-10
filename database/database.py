import aiosqlite
from datetime import datetime

DB_NAME = "blinkit.db"


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS tracked_products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT UNIQUE,
            name TEXT,
            url TEXT,
            last_stock INTEGER DEFAULT -1,
            last_checked DATETIME,
            created_at DATETIME
        )
        """)
        await db.commit()


async def add_product(product_id: str, name: str, url: str, last_stock: int):
    async with aiosqlite.connect(DB_NAME) as db:
        now = datetime.now().isoformat()
        await db.execute("""
        INSERT INTO tracked_products (product_id, name, url, last_stock, last_checked, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(product_id) DO UPDATE SET
            name = excluded.name,
            url = excluded.url,
            last_stock = excluded.last_stock,
            last_checked = excluded.last_checked
        """, (product_id, name, url, last_stock, now, now))
        await db.commit()


async def get_all_products():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tracked_products") as cursor:
            return await cursor.fetchall()


async def update_stock(product_id: str, last_stock: int):
    async with aiosqlite.connect(DB_NAME) as db:
        now = datetime.now().isoformat()
        await db.execute("""
        UPDATE tracked_products 
        SET last_stock = ?, last_checked = ? 
        WHERE product_id = ?
        """, (last_stock, now, product_id))
        await db.commit()


async def remove_product(product_id: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM tracked_products WHERE product_id = ?", (product_id,))
        await db.commit()
