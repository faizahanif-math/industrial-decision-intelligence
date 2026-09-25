import bcrypt
import psycopg

# Neon connection
HOST = "ep-broad-hall-b5onbloe-pooler.c-7.us-east-2.aws.neon.tech"
DB = "neondb"
USER = "neondb_owner"
NEON_PASSWORD = input("Neon password (jo abhi copy kiya tha): ").strip()

username = input("Login username (default: admin): ").strip() or "admin"
full_name = input("Full Name (default: Administrator): ").strip() or "Administrator"
password = input("Login password (jo dashboard mein use karna hai): ").strip()

password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

conn = psycopg.connect(
    host=HOST, port=5432, dbname=DB,
    user=USER, password=NEON_PASSWORD,
    sslmode="require"
)

with conn.cursor() as cur:
    cur.execute("""
        INSERT INTO users (username, password_hash, full_name, role)
        VALUES (%s, %s, %s, 'ADMIN')
        ON CONFLICT (username) DO UPDATE
        SET password_hash = EXCLUDED.password_hash;
    """, (username, password_hash, full_name))
    conn.commit()

print(f"\n✅ Admin user '{username}' created on Neon!")
conn.close()