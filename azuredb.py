import pyodbc
import os

RESOURCE_GROUP = 'EcomWebsiteRG'
LOCATION = 'eastus'  # example Azure availability zone, should match resource group
SQL_SERVER = 'ecommercewebsite2.database.windows.net'
SQL_DB = 'UserDatabase'
USERNAME = os.environ['SQL_DB_USERNAME']
PASSWORD = os.environ['SQL_DB_PASSWORD']

class sql_connection:
    def __init__(self):
        self.driver= '{ODBC Driver 17 for SQL Server}'
        self.conn = pyodbc.connect('DRIVER='+self.driver+';SERVER='+SQL_SERVER+';PORT=1433;DATABASE='+SQL_DB+';UID='+USERNAME+';PWD='+ PASSWORD)
        self.cursor = self.conn.cursor()
    def add_user_to_db(self, userId, email, firstName, lastName, address1, address2, zipcode, city, state, country, phone):
        self.cursor.execute(f"INSERT INTO users  VALUES ({userId},'{email}','{firstName}','{lastName}','{address1}','{address2}','{zipcode}','{city}','{state}','{country}','{phone}')")
        self.cursor.commit()
    def remove_user_from_db(self,email):
        self.cursor.execute(f"DELETE from users WHERE CONVERT(VARCHAR, email)='{email}'")
        self.cursor.commit()
    def execute(self, cursor, query):
        self.cursor.execute(query)
        self.cursor.commit()
