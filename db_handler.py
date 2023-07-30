import pymongo
from pymongo import MongoClient
from pymongo.database import Database
class DBhandle:
    def __init__(self, in_docker = False):
        self.client: MongoClient = MongoClient("mongodb://host.docker.internal:27017") if in_docker else MongoClient()
        self.db: Database = None

    def set_db(self, database:str):
        self.db = self.client.get_database(database)

    def disconnect(self):
        self.client.close()

if __name__ == "__main__":
    
    #for db updates
    handle = DBhandle()
    handle.set_db("bot")
    handle.disconnect()