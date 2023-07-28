import pymongo
from pymongo import MongoClient
from pymongo.database import Database

class DBhandle:
    def __init__(self, host = None, port = None):
        self.client: MongoClient = MongoClient(host,port)
        self.db: Database = None

    def set_db(self, database:str):
        self.db = self.client.get_database(database)

    def disconnect(self):
        self.client.close()

if __name__ == "__main__":
    
    #for db updates
    handle = DBhandle()
    handle.open_db("bot")
