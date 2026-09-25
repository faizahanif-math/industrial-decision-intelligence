import psycopg
from getpass import getpass

password = getpass("Enter PostgreSQL password: ")

try:
    connection = psycopg.connect(
        host="localhost",
        port=5432,
        dbname="industrial_decision_db",
        user="postgres",
        password=password
    )

    print("Database connection successful!")

    connection.close()

except Exception as e:
    print("Connection failed:")
    print(e)