import sqlite3
from hashlib import sha256

def hash_password(password):
    return sha256(password.encode()).hexdigest()

def init_db():
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        password TEXT NOT NULL,
                        approved BOOLEAN NOT NULL DEFAULT 0,
                        store_id INTEGER,
                        FOREIGN KEY(store_id) REFERENCES stores(id)
                    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS stores (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL
                    )''')
    
    # Create an admin user
    admin_username = "admin"
    admin_password = hash_password("admin123")  # Admin password is 'admin123'
    try:
        cursor.execute("INSERT INTO users (username, password, approved) VALUES (?, ?, 1)", (admin_username, admin_password))
    except sqlite3.IntegrityError:
        # Admin user already exists
        pass

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
