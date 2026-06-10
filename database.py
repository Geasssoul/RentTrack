import sqlite3
import os

DB_PATH = "data/rental.db"


# 创建数据库
def create_database():

    os.makedirs("data", exist_ok=True)

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    # 房产
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS properties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        address TEXT
    )
    """)

    # 租客
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tenants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        property_id INTEGER
    )
    """)

    conn.commit()
    conn.close()


create_database()


def get_connection():
    return sqlite3.connect(DB_PATH)


# -------------------------
# Properties
# -------------------------

def add_property(name, address):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO properties(name, address)
        VALUES(?, ?)
        """,
        (name, address)
    )

    conn.commit()
    conn.close()


def get_properties():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, name, address
        FROM properties
        ORDER BY id DESC
        """
    )

    rows = cursor.fetchall()

    conn.close()

    return rows


# -------------------------
# Tenants
# -------------------------

def add_tenant(name, phone, email, property_id):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO tenants(
            name,
            phone,
            email,
            property_id
        )
        VALUES(?, ?, ?, ?)
        """,
        (
            name,
            phone,
            email,
            property_id
        )
    )

    conn.commit()
    conn.close()


def get_tenants():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            tenants.id,
            tenants.name,
            tenants.phone,
            tenants.email,
            properties.name
        FROM tenants
        LEFT JOIN properties
        ON tenants.property_id = properties.id
        ORDER BY tenants.id DESC
        """
    )

    rows = cursor.fetchall()

    conn.close()

    return rows