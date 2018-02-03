class Member:

    def __init__(self, id, username, ip, port):
        self.id = id
        self.username = username
        self.ip = ip
        self.port = port

    def __str__(self):
        return ','.join([self.id, self.username, self.ip, self.port])

