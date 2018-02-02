import random


class Group:

    def __init__(self, group_name):
        self.name = group_name
        self.members_list = []
        # self.multicast_addr = self.generate_multicast_addr()
        # self.multicast_port = self.generate_multicast_port()

    # add a specific member to the group
    def add_member(self, member):
        if member not in self.members_list:
            self.members_list.append(member)

    # remove a member from the group
    def remove_member(self, member):
        self.members_list.remove(member)

    # list all the active members of the group
    def list_members(self):
        users = ""
        for member in self.members_list:
            users = users + '(' + str(member.username) + '), '
        # remove extra comma at the end of the active groups list
        users.rstrip(',')
        return users

    '''
    # auto-generate a random multicast address from the range
    # 224.0.0.0 - 224.255.255.255
    @staticmethod
    def generate_multicast_addr():
        multicast = '224.'.join(str(random.randint(0, 255)) for _ in range(3))
        return multicast

    # auto-generate a random port (port 10000 - 50000) that all
    # peers on the specific multicast group will be listening on
    @staticmethod
    def generate_multicast_port():
        port = random.randint(10000, 50000)
        return port
    '''