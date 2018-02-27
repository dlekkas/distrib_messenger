import sys


class Metrics:

    def __init__(self, total_messages_sent=0, total_messages_received=0, start_time=0.0, end_time=0.0):
        self.total_messages_sent = total_messages_sent
        self.total_messages_received = total_messages_received
        self.start_time = start_time
        self.end_time = end_time
        # dictionary with key = <message-id> and value = tuple (<send-time>, <deliver-time)
        self.latency_list = {}

    # calculate throughput by dividing the total messages sent by the time elapsed
    # between the first message and the delivery of the last message
    def calculate_throughput(self):
        total_elapsed_time = self.end_time - self.start_time
        if total_elapsed_time != 0:
            throughput = total_elapsed_time / self.total_messages_sent
        else:
            throughput = 0
        return throughput

    # calculate system's average latency
    def calculate_avg_latency(self):
        total_latency = 0.0
        for tup in self.latency_list.values():
            latency = tup[1] - tup[0]
            total_latency = total_latency + latency
        if len(self.latency_list) != 0:
            avg_latency = total_latency / len(self.latency_list)
        else:
            avg_latency = 0
        return avg_latency

    def print_info(self, output_fd=sys.stdout):
        """
        Print the following metrics to evaluate messenger system's performance:
        System throughput - how many messages are served over time
        System latency - average message delivery time
        Messages cost - total messages sent/received

        :param output_fd: file descriptor to output performance data
        """
        throughput = self.calculate_throughput()
        avg_latency = self.calculate_avg_latency()
        total_messages = self.total_messages_sent + self.total_messages_received
        output_fd.write('-----Performance analytics -----')
        output_fd.write('System throughput = %.3f messages/sec' % throughput)
        output_fd.write('System latency = %.3f ms' % avg_latency)
        output_fd.write('Messages sent = %d' % self.total_messages_sent)
        output_fd.write('Messages received = %d' % self.total_messages_received)
        output_fd.write('Total messages = %d' % total_messages)
