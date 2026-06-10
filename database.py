import sqlite3


DB_PATH = "data/rental.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


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