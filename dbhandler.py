import shelve

class DBhandle:
    def __init__(self):
        self.handle = None
        self.live = False
    def open(self):
        self.handle = shelve.open("dbfolder/localdict")
        self.live = True
    def update(self, key, value):
        if self.live:
            self.handle[key] = value
        else:
            print("db not live")
    def get(self, key):
        if self.live:
            return self.handle[key]
    def close(self):
        self.handle.close()