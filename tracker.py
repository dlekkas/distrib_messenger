import socket
import select
import member
import group


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
        # create socket to listen for all the clients and
        # ensure reliable connection with TCP for control messages
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(0)
        self.socket.bind((self.host, self.port))
        self.socket.listen(self.max_listen)

        self.sockets_list.append(self.socket)

        print 'Chat server started listening on port ' + str(self.port)

        while True:
            readers, writers, errors = select.select(self.sockets_list, [], [])
            for sock in readers:
                # new connection established
                if sock == self.socket:
                    self.serve_client()
                # command issued by member
                else:
                    print 'Handling request ...'
                    self.handle_request(sock)


    def serve_client(self):
        # accept a client incoming connection
        sockfd, addr = self.socket.accept()
        # set the client socket to not block
        sockfd.setblocking(0)
        self.sockets_list.append(sockfd)
        print 'Client' + str(addr) + 'connected successfully!'


    def handle_request(self, socket):
        message = socket.recv(4096)
        print message
        if message:
            print 'Client [' + str(socket.getpeername()) + '] sent "' + str(message) + '"'

            # if  message starts with 'register' word then a client
            # wants to register to our service
            if message[0:8] == 'register':
                self.client_register(socket, message)
            #  a client command is issued
            else:
                command = message.split("\t")
                if command[1] == '!q':
                    # user's ID is expected as first argument of the message
                    member_id = command[0]
                    self.member_quit(member_id, socket)
                elif command[1] == '!lg':
                    self.list_groups(socket)


    def list_groups(self, socket):
        active_groups = ""
        for group in self.groups:
            group_name = group[0]
            active_groups = active_groups + '[' + group_name + '], '

        # remove extra comma at the end of the active groups list
        active_groups.rstrip(',')
        # respond to client's request by sending the active groups
        self.send_message(socket, active_groups)


    def member_quit(self, member_id, socket):
        if socket in self.sockets_list:
            self.sockets_list.remove(socket)
            socket.close()
        # member object that wants to quit
        member = self.members_dict[member_id]
        # TODO - remove member from each group


    def join_group(self, client, group, socket):
        # TODO - return multicast_ip and multicast port tab delimited to client
        pass


    # handle the new member registration by creating a new member
    # entry and by generating a unique ID for the new member
    def client_register(self, socket, message):
        hash_salt = "%SALT%"
        register_info = message.split('\t')
        client_ip = register_info[1]
        client_port = register_info[2]
        client_username = register_info[3]
        # generate a unique ID for each client
        client_id = str(hash(client_username + hash_salt))
        # create a member object for the new member
        new_member = member.Member(client_id, client_username, client_ip, client_port)
        # add a dictionary entry for each client based on his unique ID
        self.members_dict[client_id] = new_member
        self.send_message(socket, new_member.id)


    # this function sends the desired response to user's control message
    # and terminates the TCP connection to ensure resources preservation
    def send_message(self, socket, message):
        socket.send(message)
        self.sockets_list.remove(socket)
        socket.close()


server = Tracker(host="192.168.1.22",port=52237)
server.connect()








