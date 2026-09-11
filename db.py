import os
import pymysql

from dotenv import load_dotenv

load_dotenv() # carrefa as infos do .env

def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "estoque"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor, # linhas viram dict

    )

