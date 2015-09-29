import random

from BasicTest import *

"""
This test sends Dupplicate Ack
"""
class DuplicateAckTest(BasicTest):
    def handle_packet(self):
        for p in self.forwarder.in_queue:
            if random.randint(0,1):
                #append same packet 10 times
                for i in range(0,10):
                    self.forwarder.out_queue.append(p)
            else :
                self.forwarder.out_queue.append(p)

        # empty out the in_queue
        self.forwarder.in_queue = []