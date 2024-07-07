import psycopg2
from psycopg2 import sql

# Database connection parameters
db_params = {
    'dbname': 'web_crawler',
    'user': 'root',
    'password': 'arka1256',
    'host': 'localhost',
    'port': '5432'
}

def get_all_tables(cursor):
    """Retrieve all table names from the public schema."""
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
    """)
    tables = cursor.fetchall()
    return [table[0] for table in tables]

def fetch_table_content(cursor, table_name):
    """Fetch all content from a given table."""
    cursor.execute(sql.SQL("SELECT * FROM {}").format(sql.Identifier(table_name)))
    rows = cursor.fetchall()
    column_names = [desc[0] for desc in cursor.description]
    return column_names, rows

def main():
    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()

        # Get all tables
        tables = get_all_tables(cursor)

        for table in tables:
            print(f"\nContent of table: {table}")
            column_names, rows = fetch_table_content(cursor, table)

            # Print column names
            print(column_names)

            # Print all rows
            for row in rows:
                print(row)

    except Exception as error:
        print(f"Error: {error}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
