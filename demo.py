import random
from client import Client

TRACKER_PORT = 50000


# generate random port from 10000-50000
def generate_random_port():
    return random.randint(10000, 50000)


def generate_random_username():
    usernames = ['andrew', 'dimitris', 'alex', 'haris', 'bill', 'tom', 'jack']
    return usernames[random.randrange(0, len(usernames))]


user_ip = '127.0.0.1'
tcp_port = generate_random_port()
udp_port = generate_random_port()
username = generate_random_username()

user = Client(user_ip, tcp_port, udp_port)
print 'Client [IP=%s, TCP_PORT=%s, UDP_PORT=%s] ' % (user_ip, tcp_port, udp_port)
user.register(user_ip, TRACKER_PORT)
