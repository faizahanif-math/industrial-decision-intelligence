import tomllib
import psycopg

with open(".streamlit/secrets.toml", "rb") as f:
    s = tomllib.load(f)["postgres"]

conn = psycopg.connect(
    host=s["host"],
    port=s["port"],
    dbname=s["dbname"],
    user=s["user"],
    password=s["password"]
)

cur = conn.cursor()
cur.execute("""
    SELECT table_name, column_name
    FROM information_schema.columns
    WHERE table_schema = 'public'
    ORDER BY table_name, ordinal_position;
""")

for row in cur.fetchall():
    print(row[0], "|", row[1])

conn.close()