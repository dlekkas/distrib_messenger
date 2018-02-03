import socket
import sys
import re
import select

my_port = 28773
server_p = 50000
port_udp = 9999
send_port = 9998


class Client:

    def __init__(self, ip="127.0.0.1", tcp_port=my_port, udp_port=port_udp, username="alex"):
        self.ip = ip
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        self.username = username
        self.id = None
        self.udp_socket = None
        self.multi_sockets = []

    def register_and_run(self, server_ip, server_port):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind((self.ip, self.udp_port))
        self.udp_socket = s

        formatted_message = "\t".join(("register", self.ip, str(self.udp_port), self.username))
        reply = self.send_to_server(formatted_message,server_ip, server_port)
        self.id = reply
        print "Successfully registered with id: " + self.id

        while True:
            ready = select.select([sys.stdin, self.udp_socket], [], [], 0)
            for inp in ready[0]:
                if inp == sys.stdin:
                    text = sys.stdin.readline()
                    self.decode_and_forward(text, server_ip, server_port)
                else:
                    inp.settimeout(5)
                    try:
                        message = inp.recv(4096)
                    except socket.error:
                        print "Timeout Happened"
                        inp.shutdown(socket.SHUT_RDWR)
                        inp.close()
                        #sys.exit(0)
                    print message

    def list_groups(self, server_ip, server_port, message):
        tokens = message.split()
        formatted_message = "\t".join((str(self.id), tokens[0]))
        reply = self.send_to_server(formatted_message,server_ip, server_port)
        groups = reply
        print groups

    def list_members(self, server_ip, server_port, message):
        tokens = message.split()
        formatted_message = "\t".join((str(self.id), tokens[0], tokens[1]))
        reply = self.send_to_server(formatted_message,server_ip, server_port)
        members = reply
        print members

    def join_group(self, server_ip, server_port, message):
        tokens = message.split()
        formatted_message = "\t".join((str(self.id), tokens[0], tokens[1]))
        reply = self.send_to_server(formatted_message ,server_ip, server_port)
        print reply
        data = reply.split("\t")
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind((data[0], data[1]))
        self.multi_sockets.append(s)

    def exit_group(self, server_ip, server_port, message):
        tokens = message.split()
        formatted_message = "\t".join((str(self.id),tokens[0],tokens[1]))
        reply = self.send_to_server(formatted_message,server_ip, server_port)
        status = reply
        print status

    def quit(self,server_ip, server_port, message):
        tokens = message.split()
        formatted_message = "\t".join((str(self.id),tokens[0]))
        reply = self.send_to_server(formatted_message,server_ip, server_port)
        status = reply
        print status

    def send_to_server(self, message, server_ip, server_port):

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #s.bind((self.ip, self.tcp_port))
        s.connect((server_ip, server_port))
        s.send(message)

        s.settimeout(5)
        try:
            reply = s.recv(4096)
        except socket.error:
            print "Timeout Happened"
            s.shutdown(socket.SHUT_RDWR)
            s.close()
            sys.exit(0)

        s.shutdown(socket.SHUT_RDWR)
        s.close()

        return reply

    def send(self, ip, port, message):
        address = (ip, port)

        self.udp_socket.settimeout(5)
        try:
            self.udp_socket.sendto(message, address)
        except socket.error:
            print "timeout bitch"
            self.udp_socket.shutdown(socket.SHUT_RDWR)
            #self.close()

        # self.udp_socket.sendto(message, address)
        print "sent data"

    def decode_and_forward(self, message, server_ip, server_port):

        if re.match('\s*!lg\s*', message):
            self.list_groups(server_ip,server_port, message)
        elif  re.match('\s*!lm\s+[\w\d_-]+$\s*', message):
            self.list_members(server_ip,server_port, message)
        elif re.match('\s*!j\s+[\w\d_-]+$\s*', message):
            self.join_group(server_ip,server_port, message)
        elif re.match('\s*!e\s+[\w\d_-]+$\s*', message):
            self.exit_group(server_ip,server_port, message)
        elif re.match('\s*!q\s*', message):
            self.quit(server_ip,server_port,message)
        elif re.match('send', message):
            self.send('192.168.1.3', send_port, message)


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 1))
    my_ip = s.getsockname()[0]
    s.shutdown(socket.SHUT_RDWR)
    s.close()
    return my_ip


ip_ad = get_ip()
c = Client()
c.register_and_run("127.0.0.1", server_p)
