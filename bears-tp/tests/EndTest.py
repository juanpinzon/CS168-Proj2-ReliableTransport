import random

from BasicTest import *

"""
This test check nonsense data on the files
"""
class EndTest(BasicTest):
    count = 0
    def handle_packet(self):
        for p in self.forwarder.in_queue:
            if p.msg_type == 'end' and self.count < 10:
                pass
            else:
                self.forwarder.out_queue.append(p)
            self.count += 1
        # empty out the in_queue
        self.forwarder.in_queue = []