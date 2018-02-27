
class Message:

    def __init__(self, message_content, group_name, username, serial_no=0):
        self.message_content = message_content
        self.group_name = group_name
        self.username = username
        self.serial_no = serial_no

    # return a tuple that uniquely identifies a message sent
    # allowing as to consider it as a UID
    def get_id(self):
        return self.group_name, self.username, self.serial_no
