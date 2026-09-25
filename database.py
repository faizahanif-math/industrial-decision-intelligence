import psycopg

def get_connection():
    connection = psycopg.connect(
        host="localhost",
        port=5432,
        dbname="industrial_decision_db",
        user="postgres",
        password=input("Enter PostgreSQL password: ")
    )

    return connection