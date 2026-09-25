import bcrypt
import tomllib
import psycopg
from getpass import getpass

# Database connection details load karein
with open(".streamlit/secrets.toml", "rb") as f:
    s = tomllib.load(f)["postgres"]

conn = psycopg.connect(
    host=s["host"],
    port=s["port"],
    dbname=s["dbname"],
    user=s["user"],
    password=s["password"]
)

print("=== Admin User Setup ===")
username = input("Username (default: admin): ").strip() or "admin"
full_name = input("Full Name (default: Administrator): ").strip() or "Administrator"
password = getpass("Password: ")
confirm = getpass("Confirm Password: ")

if password != confirm:
    print("ERROR: Passwords do not match.")
    conn.close()
    exit()

# Password ko hash karein
password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

# User ko database mein insert karein
with conn.cursor() as cur:
    cur.execute("""
        INSERT INTO users (username, password_hash, full_name, role)
        VALUES (%s, %s, %s, 'ADMIN')
        ON CONFLICT (username) DO NOTHING
        RETURNING user_id;
    """, (username, password_hash, full_name))
    result = cur.fetchone()
    conn.commit()

if result:
    print(f"\nSUCCESS: Admin user '{username}' created (user_id = {result[0]}).")
else:
    print(f"\nNOTE: User '{username}' already exists. Nothing changed.")

conn.close()