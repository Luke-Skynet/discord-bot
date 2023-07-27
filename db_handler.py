import pymongo
from pymongo import MongoClient
from pymongo.database import Database

class DBhandle:
    def __init__(self, host = None, port = None):
        self.client: MongoClient = MongoClient(host,port)
        self.db: Database = None

    def open_db(self, database:str):
        self.db = self.client.get_database(database)

    def add_doc(self, collection:str, document:dict):
        self.db[collection].insert_one(document)

    def get_doc(self, collection:str, query:dict, single = True):
        if single:
            return self.db[collection].find_one(query)
        else:
            return list(self.db[collection].find(query))
    
    def update_doc(self, collection:str, query:dict, action:dict):
        self.db[collection].update_many(query, action)

    def drop_doc(self, collection:str, query:dict, single = True):
        self.db[collection].remove(query, {"justOne": single})

    def close(self):
        self.db = None

    def disconnect(self):
        self.client.close()
