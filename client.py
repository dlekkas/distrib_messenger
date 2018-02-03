import socket
import sys
import re
import select
import member
import group

port_tcp = 6005
port_server = 50000
port_udp = 7005


class Client:

    def __init__(self, ip, tcp_port, udp_port, username="ben"):
        self.ip = ip
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        self.username = username
        self.id = None
        self.udp_socket = None
        self.group_list = {}
        self.current_group = None

    # register to service, enable cli, and wait for multicast messages
    def register_and_run(self, server_ip, server_port):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind((self.ip, self.udp_port))
        self.udp_socket = s

        formatted_message = "\t".join(("register", self.ip, str(self.udp_port), self.username))
        reply = self.send_to_server(formatted_message, server_ip, server_port)
        self.id = reply
        if reply == "username taken":
            print "user already exists. Repeat with different username"
        else:
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
                            sys.exit(0)
                        print message

    # list all groups seen by tracker
    def list_groups(self, server_ip, server_port, message):
        tokens = message.split()
        formatted_message = "\t".join((str(self.id), tokens[0]))
        reply = self.send_to_server(formatted_message,server_ip, server_port)
        groups = reply
        print groups

    # list members of certain group
    def list_members(self, server_ip, server_port, message):
        tokens = message.split()
        formatted_message = "\t".join((str(self.id), tokens[0], tokens[1]))
        reply = self.send_to_server(formatted_message,server_ip, server_port)
        members = reply
        print members

    # join selected group
    def join_group(self, server_ip, server_port, message):
        tokens = message.split()
        formatted_message = "\t".join((str(self.id), tokens[0], tokens[1]))
        reply = self.send_to_server(formatted_message, server_ip, server_port)
        multicast_group = group.Group(tokens[1])
        members = reply.split("\t")
        for m in members:
            member_attr = m.split(",")
            mem = member.Member(member_attr[0], member_attr[1], member_attr[2], member_attr[3])
            multicast_group.add_member(mem)
        self.group_list[tokens[1]]=multicast_group

    # exit selected group.
    def exit_group(self, server_ip, server_port, message):
        if not self.group_list:
            print 'group list empty. Cant leave group'
        else:
            tokens = message.split()
            group_name = tokens[1]
            formatted_message = "\t".join((str(self.id),tokens[0],tokens[1]))
            reply = self.send_to_server(formatted_message,server_ip, server_port)
            status = reply
            print status

            if group_name in self.group_list.keys():
                del self.group_list[group_name]
                if group_name == self.current_group.name:
                    self.current_group = None
            else:
                print 'you dont belong in a group with that name.'

    # warn tracker that you quit chat service, free udp port and exit
    def quit(self, server_ip, server_port, message):
        tokens = message.split()
        formatted_message = "\t".join((str(self.id), tokens[0]))
        reply = self.send_to_server(formatted_message, server_ip, server_port)
        status = reply
        print status
        self.udp_socket.close()
        sys.exit(0)

    # select group to send next messages. The selected group
    # is stored in  current_group private variable
    def select_group(self, message):
        tokens = message.split()
        group_name = tokens[1]
        if group_name in self.group_list.keys():
            self.current_group = self.group_list[group_name]
        else:
            print 'you dont belong in a group with that name.'

    # send data to server and return reply. Used in
    # other functions to automate this process
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

    # send multicast message to selected group
    def send_message(self, message):
        curr_group = self.current_group
        if curr_group is not None:
            curr_members = curr_group.members_list
            for mem in curr_members:
                address = (mem.ip, int(mem.port))
                formatted_message = " ".join(("in", curr_group.name, self.username, "says::", message))
                self.udp_socket.sendto(formatted_message, address)
        else:
            print 'no group to send selected. use !w <group name> to choose'

    # decode user's input and forward to responsible function
    def decode_and_forward(self, message, server_ip, server_port):

        if re.match('\s*!lg\s*', message):
            self.list_groups(server_ip,server_port, message)
        elif re.match('\s*!lm\s+[\w\d_-]+$\s*', message):
            self.list_members(server_ip,server_port, message)
        elif re.match('\s*!j\s+[\w\d_-]+$\s*', message):
            self.join_group(server_ip,server_port, message)
        elif re.match('\s*!e\s+[\w\d_-]+$\s*', message):
            self.exit_group(server_ip,server_port, message)
        elif re.match('\s*!q\s*', message):
            self.quit(server_ip,server_port,message)
        elif re.match('\s*!w\s+[\w\d_-]+$\s*', message):
            self.select_group(message)
        elif re.match('\s*[^ !].*', message):
            self.send_message(message)
        else:
            print 'not valid command'


# used to get private ip instantly
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 1))
    my_ip = s.getsockname()[0]
    s.shutdown(socket.SHUT_RDWR)
    s.close()
    return my_ip


ip_ad = get_ip()
# ip_ad = "127.0.0.1"

c = Client(ip_ad, port_tcp, port_udp)

# register to server with his ip and port
c.register_and_run("127.0.0.1", port_server)
