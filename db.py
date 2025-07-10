import mysql.connector
from mysql.connector import Error
import configparser


def create_connection():
    config = configparser.ConfigParser()
    config.read('db.ini')

    connection = None
    try:
        connection = mysql.connector.connect(
            host=config['mysql']['host'],
            user=config['mysql']['user'],
            passwd=config['mysql']['password'],
            database=config['mysql']['database']
        )
        print("Connection to MySQL DB successful")
    except Error as e:
        print(f"The error '{e}' occurred")
        exit()

    return connection





