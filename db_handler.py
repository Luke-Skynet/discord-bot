import pymongo
from pymongo import MongoClient
from pymongo.database import Database

class DatabaseHandle:
    def __init__(self, mongo_host:str = "localhost", mongo_port:int = 27017):
        self.client: MongoClient = MongoClient(host = mongo_host, port = mongo_port)
        self.db: Database = None

    def set_db(self, database:str):
        self.db = self.client.get_database(database)

    def disconnect(self):
        self.client.close()

if __name__ == "__main__":
    
    #for db updates
    handle = DatabaseHandle()
    handle.set_db("live")

    handle.disconnect()