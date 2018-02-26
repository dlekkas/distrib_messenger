import socket
import sys
import re
import select

from member import Member
from group import Group


class Client:

    def __init__(self, ip, tcp_port, udp_port):
        self.member = Member(None, None, ip, udp_port, tcp_port)
        self.udp_socket = None
        self.tcp_socket = None
        self.group_list = {}
        self.current_group = None


    def register(self, server_ip, server_port):
        # initialize UDP socket for group messages
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind((self.member.ip, self.member.udp_port))

        # initialize TCP socket listening for group change notifications from tracker
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setblocking(0)
        self.tcp_socket.bind((self.member.ip, self.member.tcp_port))
        self.tcp_socket.listen(1)

        valid_username = False
        while not valid_username:
            # prompt user to enter a username
            username = raw_input('Enter your username: ')
            # check if the username is valid (matches specific regex)
            if re.match("^[a-zA-Z0-9_.-]+$", username) is None:
                print "Username is invalid, please try again."
                continue

            # generate registration message and send to tracker
            formatted_message = "\t".join(("register", self.member.ip, str(self.member.udp_port),
                                           str(self.member.tcp_port), username))
            reply = self.send_to_server(formatted_message, server_ip, server_port)
            # check if username already exists
            if reply == "username taken":
                print "Username already exists, please try again."
                continue
            else:
                valid_username = True
                self.member.id = reply
                self.member.username = username

        print "Successfully registered to distributed messenger"
        self.run(server_ip, server_port)



    def run(self, server_ip, server_port):
            sys.stdout.write('[%s] > ' % self.member.username)
            # loop forever waiting for incoming messages from other clients and waiting for
            # user to submit a message and/or a command from stdin (all those operations
            # are non-blocking due to the use of select() function
            while True:
                sockets_list = [sys.stdin, self.udp_socket, self.tcp_socket]
                readers, writers, errors = select.select(sockets_list, [], [], 0)

                for sock in readers:
                    # the user has entered a command for the tracker or a message for a group
                    if sock == sys.stdin:
                        text = sys.stdin.readline()
                        self.decode_and_forward(text, server_ip, server_port)
                        sys.stdout.write('[%s] > ' % self.member.username)

                    # the udp socket listening for chat messages has available data to read
                    # so a member from the groups the user belongs to, has written a message
                    # that is printed to the stdout
                    elif sock == self.udp_socket:
                        sock.settimeout(5)
                        try:
                            message = sock.recv(4096)
                        except socket.error:
                            print "Timeout Happened"
                            sock.shutdown(socket.SHUT_RDWR)
                            sock.close()
                            sys.exit(0)
                        sys.stdout.write('\r%s' % message)
                        sys.stdout.write('[%s] > ' % self.member.username)

                    # the TCP socket is listening for server to notify asynchronously that
                    # a member has entered or left a group that the client belongs to
                    elif sock == self.tcp_socket:
                        # accept an incoming connection from tracker
                        sockfd, addr = self.tcp_socket.accept()
                        # set the socket to non-blocking
                        # TODO - socket should be non-blocking (but is bug prone)
                        sockfd.setblocking(1)
                        self.handle_server_notification(sockfd)

                    # unreachable state
                    else:
                        print 'This should never be displayed [1].'


    # list all available groups in the messenger chat
    def list_groups(self, server_ip, server_port, message):
        command = message.split()[0]
        formatted_message = "\t".join((str(self.member.id), command))
        reply = self.send_to_server(formatted_message, server_ip, server_port)
        print 'groups: ' + reply


    # list members of certain group
    def list_members(self, server_ip, server_port, message):
        command = message.split()[0]
        group_name = message.split()[1]
        formatted_message = "\t".join((str(self.member.id), command, group_name))
        reply = self.send_to_server(formatted_message, server_ip, server_port)
        print 'members: ' + reply


    # join selected group
    def join_group(self, server_ip, server_port, message):
        command = message.split()[0]
        group_name = message.split()[1]
        formatted_message = "\t".join((str(self.member.id), command, group_name))
        reply = self.send_to_server(formatted_message, server_ip, server_port)
        multicast_group = Group(group_name)
        members_details = reply.split("\t")
        for m in members_details:
            member_info = m.split(",")
            mem = Member(member_info[0], member_info[1], member_info[2], member_info[3], member_info[4])
            multicast_group.add_member(mem)
        self.group_list[group_name] = multicast_group


    # exit selected group.
    def exit_group(self, server_ip, server_port, message):
        if not self.group_list:
            print 'No available groups exist.'
        else:
            command = message.split()[0]
            group_name = message.split()[1]
            formatted_message = "\t".join((str(self.member.id), command, group_name))
            reply = self.send_to_server(formatted_message, server_ip, server_port)
            # TODO - error handle a reply different than 'EXIT_GROUP OK'

            if group_name in self.group_list.keys():
                del self.group_list[group_name]
                if (self.current_group is not None) and (group_name == self.current_group.name):
                    self.current_group = None
            else:
                print "You don\'t belong in group '%s'." % group_name


    # warn tracker that you quit chat service, free udp port and exit
    def quit(self, server_ip, server_port, message):
        tokens = message.split()
        formatted_message = "\t".join((str(self.member.id), tokens[0]))
        reply = self.send_to_server(formatted_message, server_ip, server_port)
        # TODO - error handle a reply different than 'QUIT OK'

        self.udp_socket.close()
        self.tcp_socket.close()
        print 'Terminating messenger application ...'
        sys.exit(0)


    # select group to send next messages. The selected group
    # is stored in  current_group private variable
    def select_group(self, message):
        group_name = message.split()[1]
        if group_name in self.group_list.keys():
            self.current_group = self.group_list[group_name]
        else:
            print "You don't belong in group '%s'." % group_name


    # send data to server and return reply. Used in
    # other functions to automate this process
    def send_to_server(self, message, server_ip, server_port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((server_ip, server_port))
        s.send(message)
        s.settimeout(5)
        try:
            reply = s.recv(4096)
        except socket.error:
            sys.stderr.write("socket timeout")
            s.shutdown(socket.SHUT_RDWR)
            s.close()
            sys.exit(0)
        s.shutdown(socket.SHUT_RDWR)
        s.close()
        return reply


    def handle_server_notification(self, socket):
        message = socket.recv(4096)
        if message:
            # debug message to print the message sent by tracker
            # print 'Tracker [' + str(socket.getpeername()) + '] sent notification "' + str(message) + '"'
            notification = message.split("\t")
            operation = notification[0]
            group_name = notification[1]
            group = self.group_list[group_name]
            member_info = notification[2].split(',')

            # add the new member to client's group view in order to be
            # able to send him messages
            if operation == 'add':
                new_member = Member(member_info[0], member_info[1], member_info[2],
                                    member_info[3], member_info[4])
                group.add_member(new_member)
            # remove the member from client's group view
            elif operation == 'remove':
                member_name = member_info[1]
                group.remove_member_by_name(member_name)
            else:
                print '[handle_server_notification] Operation not supported'
                sys.exit(2)


    # send multicast message to selected group
    def send_message(self, message):
        curr_group = self.current_group
        if curr_group is not None:
            curr_members = curr_group.members_list
            for mem in curr_members:
                address = (mem.ip, int(mem.udp_port))
                formatted_message = " ".join(("in", curr_group.name, self.member.username, "says::", message))
                self.udp_socket.sendto(formatted_message, address)
        else:
            print 'No group to send selected. use !w <group name> to choose'


    # decode user's input and forward to responsible function
    def decode_and_forward(self, message, server_ip, server_port):
        if re.match('\s*!lg\s*', message):
            self.list_groups(server_ip, server_port, message)
        elif re.match('\s*!lm\s+[\w\d_-]+$\s*', message):
            self.list_members(server_ip, server_port, message)
        elif re.match('\s*!j\s+[\w\d_-]+$\s*', message):
            self.join_group(server_ip, server_port, message)
        elif re.match('\s*!e\s+[\w\d_-]+$\s*', message):
            self.exit_group(server_ip, server_port, message)
        elif re.match('\s*!q\s*', message):
            self.quit(server_ip, server_port, message)
        elif re.match('\s*!w\s+[\w\d_-]+$\s*', message):
            self.select_group(message)
        elif re.match('\s*[^ !].*', message):
            self.send_message(message)
        else:
            print 'invalid command'

