class Member:

    def __init__(self, id, username, ip, udp_port, tcp_port):
        self.id = id
        self.username = username
        self.ip = ip
        self.udp_port = udp_port
        self.tcp_port = tcp_port

    def __str__(self):
        return ','.join([self.id, self.username, self.ip, self.udp_port, self.tcp_port])

