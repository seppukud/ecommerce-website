import logging
import base64
import json
import pyodbc


import azure.functions as func
import os
import sendgrid
from sendgrid.helpers.mail import *


RESOURCE_GROUP = 'EcomWebsiteRG'
LOCATION = 'eastus'  # example Azure availability zone, should match resource group

#SQL_SERVER = 'sqlserverecom.database.windows.net'
SQL_SERVEER = 'ecommercewebsite2.database.windows.net'
SQL_DB = 'UserDatabase'
#USERNAME = 'user1'
USERNAME = 'minh'
#PASSWORD = os.environ["SQL_DB_Password"]
PASSWORD = 'Shine1011$'

class sql_connection:
    def __init__(self):
        self.driver= '{ODBC Driver 17 for SQL Server}'
        self.conn = pyodbc.connect('DRIVER='+self.driver+';SERVER='+SQL_SERVER+';PORT=1433;DATABASE='+SQL_DB+';UID='+USERNAME+';PWD='+ PASSWORD)
        self.cursor = self.conn.cursor()
    def execute(self, cursor, query):
        self.cursor.execute(query)
        self.cursor.commit()



def main(msg: func.QueueMessage) -> None:
    msg_body = msg.get_body().decode('utf-8')
    logging.info('Python queue trigger function processed a queue item: %s',
                 msg_body)
    data = base64.b64decode(msg_body).decode()
    data_json = json.loads(data)
    orderId = data_json['orderId']
    with sql_connection().conn as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE orders SET status = 'DISPATCHED' WHERE userId = {data_json['userId']} and orderId={orderId}")
        conn.commit()
        logging.info(f'OrderId:{orderId} updated to dispatched in table')
        cur.execute(f"SELECT email FROM users where CONVERT(VARCHAR, userid)={data_json['userId']}")
        email_id = cur.fetchone()[0]
    conn.close()


    #Send mail notifying order dispatched

    logging.info(f'Sending mail to :{email_id} . ')
    sg = sendgrid.SendGridAPIClient(os.environ["SENGRID_API_KEY"])
    from_email = Email("rj.ietf@gmail.com")
    to_email = To(email_id)
    subject = f"Order ID:{data_json['orderId']} is dispatched."
    content = Content("text/plain", f"We have dispatched your order:{data_json['orderId']}. But don't expect to receive it :-p")
    mail = Mail(from_email, to_email, subject, content)
    response = sg.client.mail.send.post(request_body=mail.get())
