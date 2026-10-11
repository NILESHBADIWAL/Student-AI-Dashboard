import mysql.connector
from mysql.connector import Error

from config import DATABASE_CONFIG


class Database:

    def __init__(self):
        self.connection = None

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=DATABASE_CONFIG["host"],
                user=DATABASE_CONFIG["user"],
                password=DATABASE_CONFIG["password"],
                database=DATABASE_CONFIG["database"],
                connection_timeout=5,
                read_timeout=5,
                write_timeout=5,
            )

            if self.connection.is_connected():
                print("MySQL connected successfully!")
                return True

        except Error as error:
            print("MySQL connection error:")
            print(error)
            raise RuntimeError(
                "Unable to connect to the chatbot database."
            ) from error

    def get_connection(self):
        if (
            self.connection is None
            or not self.connection.is_connected()
        ):
            self.connect()

        return self.connection

    def close(self):
        try:
            if (
                self.connection
                and self.connection.is_connected()
            ):
                self.connection.close()
                print("MySQL connection closed.")

        except Error as e:
            print("Error closing MySQL connection:")
            print(e)
