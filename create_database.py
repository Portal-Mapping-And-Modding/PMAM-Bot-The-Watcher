import sqlite3

def main():
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()
    cursor.execute("CREATE TABLE users (id INT , exp INT);")
    connection.commit()
    connection.close()

if __name__ == "__main__":
    main()
