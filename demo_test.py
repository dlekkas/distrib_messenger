import getpass
import random
import sys

from client import Client

SERVER_IP = '127.0.0.1'
SERVER_PORT = 50000




# generate random port from 10000-50000
def generate_random_port():
    return random.randint(2000, 10000)


def main():
    ip = '127.0.0.1'
    port = generate_random_port()
    client = Client(ip, port)
    unix_user = getpass.getuser()
    client = Client(ip, port)
    if len(sys.argv) == 2:
        input_file = sys.argv[1]
        input_fd = open(input_file, 'r')
        client.register(SERVER_IP, SERVER_PORT, input_fd, unix_user)
    else:
        print 'Usage: ./demo_test.py <input_file>'


if __name__ == "__main__":
    main()