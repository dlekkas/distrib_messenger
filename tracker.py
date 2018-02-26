import socket
import select
import logging

from group import Group
from member import Member

LOGGING_FILE = 'tracker.log'

# Configure a custom logger for debugging purposes
logging.basicConfig(
        filename=LOGGING_FILE,
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.DEBUG,
        datefmt='%d-%m-%Y %H:%M:%S')


class Tracker:

    def __init__(self, host, port, max_listen=1):
        self.host = host
        self.port = port
        # the number of max clients server will be listening on
        self.max_listen = max_listen
        # tracker's socket listening for incoming connections
        self.socket = None
        # dictionary with (key, value) = (group, list with member IDs of key group)
        self.groups = {}
        # list keeping track of the active sockets connected
        self.sockets_list = []
        # dictionary keeping connection info for each user connected
        # to our service based on his unique ID
        self.members_dict = {}


    def connect(self):
        # create non-blocking TCP socket to listen for all the clients
        # and ensure reliable connection for control messages
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(0)
        self.socket.bind((self.host, self.port))
        self.socket.listen(self.max_listen)
        self.sockets_list.append(self.socket)

        logging.info('Chat server started listening on port ' + str(self.port))

        while True:
            readers, writers, errors = select.select(self.sockets_list, [], [])
            for sock in readers:
                # new connection established
                if sock == self.socket:
                    self.serve_client()
                # command issued by member
                else:
                    self.handle_request(sock)


    def serve_client(self):
        # accept a client incoming connection
        sockfd, addr = self.socket.accept()
        # set the client socket to non-blocking
        sockfd.setblocking(0)
        self.sockets_list.append(sockfd)
        logging.debug('TCP connection with client [' + str(addr) + '] established successfully.')


    def handle_request(self, socket):
        message = socket.recv(4096)
        if message:
            # debug message to print the message sent by a specific client
            logging.info('Client [' + str(socket.getpeername()) + '] issued command "' + str(message) + '"')

            # if  message starts with 'register' word then a client
            # wants to register to our service
            if message[0:8] == 'register':
                self.client_register(socket, message)

            # a client command is issued by a specific member
            else:
                # commands start with the requesting member's ID
                # and they are tab delimited
                command = message.split("\t")
                member_id = command[0]
                if member_id in self.members_dict.keys():
                    member = self.members_dict[member_id]
                else:
                    print 'Invalid member ID issued command'
                    return

                # command "!q" informs the tracker that the member
                # that issued the command want to quit
                if command[1] == '!q':
                    self.member_quit(member)
                    self.send_message(socket, "QUIT OK")

                # command "!lg", user requests the list of all active groups
                elif command[1] == '!lg':
                    self.send_message(socket, self.list_groups())

                # command "!j <group-name>", user requests from tracker
                # to participate in the specified group
                elif command[1] == '!j':
                    group = self.join_group(member, command[2])
                    reply = "\t".join([str(member) for member in group.members_list])
                    self.send_message(socket, reply)
                    self.notify_group(group, member, 'add')
                
                # command "!lm <group-name>", user requests the list of all
                # active members in the specified group
                elif command[1] == '!lm':
                    group = self.groups[command[2]]
                    self.send_message(socket, group.list_members())

                # command "!e <group-name>", user requests to leave from
                # the specified group
                elif command[1] == '!e':
                    group_name = command[2]
                    self.leave_group(member, group_name)
                    group = self.groups[group_name]
                    self.notify_group(group, member, 'remove')
                    self.send_message(socket, "EXIT_GROUP OK")

                else:
                    logging.warning('Unrecognised command request')
                    return


    def list_groups(self):
        active_groups = ", ".join(["[%s]" % group_name for group_name in self.groups.keys()])
        return active_groups


    # member quits the application
    def member_quit(self, member):
        # remove member from every group that it belongs
        for group in self.groups.values():
            if member in group.members_list:
                group.remove_member(member)
        # remove member from the dictionary that tracker keeps
        # for all of the connected members
        del self.members_dict[member.id]


    # add a new member to the requested group
    def join_group(self, member, group_name):
        # if the group name the user requested to join doesn't exist
        # then create a new group with that name
        if group_name not in self.groups:
            new_group = Group(group_name)
            self.groups[group_name] = new_group
        # add the requesting member to the group he requested
        self.groups[group_name].add_member(member)
        return self.groups[group_name]


    # notify all members in the group that a member has been added
    # or removed from their group, the tracker informs members of the
    # group for the important changes in the following manner:
    # 'add  <group-name>    <member-info>' -> for new member
    # 'remove   <group-name>    <member-info>'  -> for leaving group
    def notify_group(self, group, member, operation):
        notification = "\t".join([operation, group.name, str(member)])
        for client in group.members_list:
            # no need to notify the new member or the member leaving the group
            if member == client:
                continue
            # create socket for each member and send notification message
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((client.ip, int(client.tcp_port)))
            sock.send(notification)
            addr = sock.getpeername()
            logging.info('Tracker sent "' + notification + '" to client [' + str(addr) + '].')
            sock.close()
            logging.debug('TCP connection with client [' + str(addr) + '] terminated successfully.')



    # remove a member from a group
    def leave_group(self, member, group_name):
        if group_name in self.groups.keys():
            group = self.groups[group_name]
            group.remove_member(member)


    # handle the new member registration by creating a new member
    # entry and by generating a unique ID for the new member
    def client_register(self, socket, message):
        register_info = message.split('\t')
        client_ip = register_info[1]
        client_port = register_info[2]
        client_l_port = register_info[3]
        client_username = register_info[4]
        # check if an active member already uses that username
        for member in self.members_dict.values():
            if member.username == client_username:
                self.send_message(socket, "username taken")
                return
        # generate a unique ID for each client
        client_id = str(hash(client_username))
        # create a member object for the new member
        new_member = Member(client_id, client_username, client_ip, client_port, client_l_port)
        # add a dictionary entry for new member based on his unique ID
        self.members_dict[client_id] = new_member
        # send the unique ID to the client
        self.send_message(socket, new_member.id)


    # this function sends the desired response to user's control message
    # and terminates the TCP connection to ensure resources preservation
    def send_message(self, socket, message):
        socket.send(message)
        addr = socket.getpeername()
        logging.info('Tracker sent "' + message + '" to client [' + str(addr) + '].')
        self.sockets_list.remove(socket)
        socket.close()
        logging.debug('TCP connection with client [' + str(addr) + '] terminated successfully.')


server = Tracker(host="127.0.0.1", port=50000)
server.connect()









