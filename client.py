import socket
import sys
import re
import select
import time
import random

from member import Member
from group import Group
from message import Message
from metrics import Metrics


class Client:

    def __init__(self, ip, udp_port, mode='FIFO'):
        self.member = Member(None, None, ip, udp_port, self.generate_random_port())
        self.udp_socket = None
        self.tcp_socket = None
        self.tracker_ip = None
        self.tracker_port = None
        self.input_fd = None
        if (mode != 'FIFO') and (mode != 'TOTAL_ORDER'):
            print 'Unsupported message ordering mode'
            sys.exit(3)
        else:
            self.mode = mode
        # dictionary of all groups this client belongs to
        self.group_list = {}
        # the group client has selected to send messages
        self.current_group = None
        # serial number of message sent by client
        self.message_num = 0
        # lamport vector implementation for FIFO ordering implemented as a dictionary
        # with key = <(username, group_name)> and value = <message-serial-no>
        self.lamport_dict = {}
        # buffer storing messages waiting to be delivered
        self.messages_buffer = []
        # lamport timestamp to support total ordering operation mode
        self.lamport_timestamp = 0
        # performance metrics
        self.metrics = Metrics()



    def register(self, server_ip, server_port, input_fd=sys.stdin, username=None):
        """
        Register client to the messenger application
        :param server_ip:   tracker's IP address
        :param server_port: the port tracker is listening to
        :param input_fd:    the file descriptor of the input stream (stdin is default)
        :param username:    client's username - skips username validation
        """
        self.tracker_ip = server_ip
        self.tracker_port = server_port
        self.input_fd = input_fd
        
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
            if username is None:
                username = raw_input('Enter your username: ')
            # check if the username is valid (matches specific regex)
            if re.match("^[a-zA-Z0-9_.-]+$", username) is None:
                print "Username is invalid, please try again."
                username = None
                continue

            # generate registration message and send to tracker
            formatted_message = "\t".join(("register", self.member.ip, str(self.member.udp_port),
                                           str(self.member.tcp_port), username))
            reply = self.send_to_server(formatted_message)
            # check if username already exists
            if reply == "username taken":
                print "Username already exists, please try again."
                username = None
                continue
            else:
                valid_username = True
                self.member.id = reply
                self.member.username = username

        print 'Successfully registered to messenger application!'
        sys.stderr.write('[%s] > ' % self.member.username)
        self.run()



    def run(self):
            # loop forever waiting for incoming messages from other clients and waiting for
            # user to submit a message and/or a command from stdin (all those operations
            # are non-blocking due to the use of select() function
            sockets_list = [self.input_fd, self.udp_socket, self.tcp_socket]
            while True:
                try:
                    readers, writers, errors = select.select(sockets_list, [], [], 0)
                except KeyboardInterrupt:
                    self.metrics.print_info()
                    sys.exit(0)

                # if there are not any messages received from network then deliver
                # the messages we already have by total ordering
                if (not readers) and self.mode == 'TOTAL_ORDER':
                    self.deliver_messages_TOTAL()

                for sock in readers:
                    # the user has entered a command for the tracker or a message for a group
                    if sock == self.input_fd:
                        # ensure that all clients are up and running
                        if self.current_group is not None and len(self.current_group.members_list) != 5:
                            continue
                        text = self.input_fd.readline()
                        if text == "":
                            sockets_list.remove(self.input_fd)
                            continue
                        self.decode_and_forward(text)
                        sys.stderr.write('[%s] > ' % self.member.username)
                        if self.mode == 'TOTAL_ORDER':
                            break

                    # the udp socket listening for chat messages has available data to read
                    # so a member from the groups the user belongs to, has written a message
                    # that is printed to the stdout
                    elif sock == self.udp_socket:
                        sock.settimeout(5)
                        try:
                            received_msg = sock.recv(4096)
                        except socket.error:
                            print "Timeout Happened"
                            sock.shutdown(socket.SHUT_RDWR)
                            sock.close()
                            sys.exit(1)
                        if self.mode == 'FIFO':
                            self.handle_incoming_message_FIFO(received_msg)
                        elif self.mode == 'TOTAL_ORDER':
                            # if it is the first message sleep for 500 ms
                            if self.lamport_timestamp == 0:
                                time.sleep(0.5)
                            self.handle_incoming_message_TOTAL(received_msg)


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
    def list_groups(self, message):
        command = message.split()[0]
        formatted_message = "\t".join((str(self.member.id), command))
        reply = self.send_to_server(formatted_message)
        print 'groups: ' + reply


    # list members of certain group
    def list_members(self, message):
        command = message.split()[0]
        group_name = message.split()[1]
        formatted_message = "\t".join((str(self.member.id), command, group_name))
        reply = self.send_to_server(formatted_message)
        print 'members: ' + reply


    # join selected group
    def join_group(self, message):
        command = message.split()[0]
        group_name = message.split()[1]
        formatted_message = "\t".join((str(self.member.id), command, group_name))
        reply = self.send_to_server(formatted_message)
        multicast_group = Group(group_name)
        members_details = reply.split("\t")
        for m in members_details:
            member_info = m.split(",")
            mem = Member(member_info[0], member_info[1], member_info[2], member_info[3], member_info[4])
            multicast_group.add_member(mem)
        self.group_list[group_name] = multicast_group


    # exit selected group.
    def exit_group(self, message):
        if not self.group_list:
            print 'No available groups exist.'
        else:
            command = message.split()[0]
            group_name = message.split()[1]
            formatted_message = "\t".join((str(self.member.id), command, group_name))
            reply = self.send_to_server(formatted_message)
            # TODO - error handle a reply different than 'EXIT_GROUP OK'

            if group_name in self.group_list.keys():
                del self.group_list[group_name]
                if (self.current_group is not None) and (group_name == self.current_group.name):
                    self.current_group = None
            else:
                print "You don\'t belong in group '%s'." % group_name


    # warn tracker that you quit chat service, free udp/tcp port and exit
    def quit(self, message):
        tokens = message.split()
        formatted_message = "\t".join((str(self.member.id), tokens[0]))
        reply = self.send_to_server(formatted_message)
        # TODO - error handle a reply different than 'QUIT OK'

        self.udp_socket.close()
        self.tcp_socket.close()
        print '\nTerminating messenger application ...\n'

        # print performance analytics information
        self.metrics.print_info()
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
    def send_to_server(self, message):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.tracker_ip, self.tracker_port))
        self.metrics.total_messages_sent += 1
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


    # check incoming message and ensure that the message is not delivered
    # unless it ensures FIFO ordering, if the message should not be
    # delivered then it is stored in the associated buffer according to
    # its group
    def handle_incoming_message_FIFO(self, received_msg):
        # each message received should be in the following form
        # <message-number> in <group-name> <username> says:: <message-content>
        message = self.parse_incoming_message(received_msg)

        # tuple associated with the incoming message (username,group_name)
        tup = (message.username, message.group_name)

        # if it is the first message received from this client then we should
        # initialize this (user,group) tuple's with a serial number of zero
        if tup not in self.lamport_dict.keys():
            self.lamport_dict[tup] = 0

        # serial number received by this message's (user,group) tuple
        last_serial = self.lamport_dict[tup]

        # if the serial number of the message received is the expected i.e the serial
        # number we have last received by this message's (user,group) tuple then
        # we accept the message and deliver it to the application (print to stdout)
        if message.serial_no == last_serial + 1:
            self.print_message(message)
            # add the delivering time of the message with specific message ID only
            # if it was sent from this client
            if message.username == self.member.username:
                delivering_time = time.time()
                self.metrics.latency_list[message.get_id()].append(delivering_time)
            self.metrics.total_messages_received += 1
            # increment serial number of this (group,username) tuple's
            self.lamport_dict[tup] = self.lamport_dict[tup] + 1
            # check if there are any messages in the buffer waiting for the recently
            # received message to be delivered and cascade deliver those messages
            updates_available = True
            while updates_available:
                for waiting_msg in self.messages_buffer:
                    if ((waiting_msg.username, waiting_msg.group_name) == tup) and \
                            (waiting_msg.serial_no == message.serial_no + 1):
                        self.print_message(waiting_msg)
                        # add the delivering time of the message with specific message ID
                        delivering_time = time.time()
                        self.metrics.latency_list[waiting_msg.get_id()].append(delivering_time)
                        self.metrics.total_messages_received += 1
                        self.messages_buffer.remove(waiting_msg)
                        continue
                updates_available = False

        # if the serial number of the message received is greater than the expected
        # then the message should be appended to the buffer
        elif message.serial_no > last_serial + 1:
            self.messages_buffer.append(message)

        # if the serial number of the message received is less than the expected
        # then the message should be rejected
        else:
            sys.stderr.write('A message is rejected due to smaller serial_no than expected')


    def handle_incoming_message_TOTAL(self, received_msg):
        # each message received should be in the following form
        # <message-number> in <group-name> <username> says:: <message-content>
        message = self.parse_incoming_message(received_msg)

        # for every receiving message, we update our local lamport timestamp
        self.lamport_timestamp = max(self.lamport_timestamp, message.serial_no) + 1

        # add the receiving message to buffer until we start delivering messages
        self.messages_buffer.append(message)



    # parse incoming message to extract important information
    # in order to implement a message ordering scheme
    def parse_incoming_message(self, received_msg):
        # each message received should be in the following form
        # <message-number> in <group-name> <username> says:: <message-content>
        tokens = received_msg.split()
        message_serial = int(tokens[0])
        group_name = tokens[2]
        username = tokens[3]
        message_content = ' '.join(tokens[5:])
        message = Message(message_content, group_name, username, message_serial)
        return message


    # print the message to the stdout and prompt the user for next command/message
    def print_message(self, message):
        # deliver message to the application according to the required format
        formatted_message = " ".join(("in", message.group_name,
                                      message.username, "says::", message.message_content))
        sys.stderr.write('\r%s' % formatted_message)
        # prompt user for next command/message
        sys.stderr.write('\n[%s] > ' % self.member.username)
        # consider each message as it was the last one
        self.metrics.end_time = time.time()


    # send multicast message to selected group
    def send_message(self, message_content):
        if self.current_group is not None:
            # update serial number of messages sent by this client
            self.message_num = self.message_num + 1


            # if it is the first sent message, then store time to calculate
            # performance metrics
            if self.message_num == 1:
                self.metrics.start_time = time.time()


            # send message to all members of the group
            for member in self.current_group.members_list:
                target_address = (member.ip, int(member.udp_port))

                if self.mode == 'FIFO':
                    msg_timestamp = self.message_num
                elif self.mode == 'TOTAL_ORDER':
                    msg_timestamp = self.lamport_timestamp

                # assert that every message sent to other clients should match the following form
                # <message-timestamp> in <group-name> <username> says:: <message-content>
                formatted_message = " ".join((str(msg_timestamp), "in", self.current_group.name,
                                              self.member.username, "says::", message_content))
                # uniquely identify this message by this tuple to calculate metrics for it
                message_id = (self.current_group.name, self.member.username, msg_timestamp)
                # evaluate time that this message was sent
                start_time = time.time()
                self.udp_socket.sendto(formatted_message, target_address)
                # add the sending time of the message with specific message ID
                self.metrics.latency_list[message_id] = [start_time]
                self.metrics.total_messages_sent += 1
        else:
            print 'No group to send selected. use !w <group name> to choose'


    def deliver_messages_TOTAL(self):
        # sorts the messages by implementing total ordering, we deliver Ti
        # iff for every j ((Ti < Tj) or (Ti = Tj and username_i < username_j))
        if self.messages_buffer:
            self.messages_buffer.sort(key=lambda x: (-x.serial_no, x.username))
        for msg in self.messages_buffer:
            self.print_message(msg)
            if msg.username == self.member.username:
                # add the delivering time of the message with specific message ID
                delivering_time = time.time()
                # store performance metrics
                self.metrics.latency_list[msg.get_id()].append(delivering_time)
                self.metrics.total_messages_received += 1
        self.messages_buffer = []



    # decode user's input and forward to responsible function
    def decode_and_forward(self, message_content):

        if re.match('\s*!lg\s*', message_content):
            self.list_groups(message_content)
        elif re.match('\s*!lm\s+[\w\d_-]+$\s*', message_content):
            self.list_members(message_content)
        elif re.match('\s*!j\s+[\w\d_-]+$\s*', message_content):
            self.join_group(message_content)
        elif re.match('\s*!e\s+[\w\d_-]+$\s*', message_content):
            self.exit_group(message_content)
        elif re.match('\s*!q\s*', message_content):
            self.quit(message_content)
        elif re.match('\s*!w\s+[\w\d_-]+$\s*', message_content):
            self.select_group(message_content)
        else:
            self.send_message(message_content)
        '''
        elif re.match('\s*[^ !].*', message_content):
            self.send_message(message_content)
        else:
            print 'Invalid command'
        '''

    # TODO - ensure that port is available
    # generate random port from 10000-50000
    def generate_random_port(self):
        return random.randint(10000, 50000)



