import random

from BasicTest import *

"""
This test check nonsense data on the files
"""
class BrokenLinkTest(BasicTest):
    count = 0
    def handle_packet(self):
        for p in self.forwarder.in_queue:
            if p.msg_type == 'data' and (self.count > 2  and self.count < 50):
                pass
            else:
                self.forwarder.out_queue.append(p)
            self.count += 1
        # empty out the in_queue
        self.forwarder.in_queue = []