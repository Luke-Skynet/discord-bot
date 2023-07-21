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
    def get(self, key, default = None):
        if self.live:
            if key in self.handle.keys():
                return self.handle[key]
            else:
                return default
    def close(self):
        self.handle.close()
        self.live = False