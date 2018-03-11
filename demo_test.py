import random
import sys
import socket

from client import Client

SERVER_HOSTNAME = 'distrib-1'
SERVER_PORT = 50000
MODE = 'TOTAL_ORDER'


# generate random port from 10000-50000
def generate_random_port():
    return random.randint(10000, 50000)


def main():
    # automatically set username as the current hostname
    username = socket.gethostname()
    # find the local ip based on the hostname
    client_ip = socket.gethostbyname(username)
    # generate a random UDP port listening for incoming connections
    port = generate_random_port()
    # find tracker ip based on its hostname
    tracker_ip = socket.gethostbyname(SERVER_HOSTNAME)

    client = Client(client_ip, port, MODE)
    if len(sys.argv) == 2:
        input_file = sys.argv[1]
        input_fd = open(input_file, 'r')
        client.register(tracker_ip, SERVER_PORT, input_fd, username)
    else:
        print 'Usage: ./demo_test.py <input_file>'


if __name__ == "__main__":
    main()