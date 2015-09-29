import random

from BasicTest import *

"""
This test check nonsense data on the files
"""
class SackNonsenseTest(BasicTest):
    def __init__(self, forwarder, input_file):
        super(SackNonsenseTest, self).__init__(forwarder, input_file, sackMode = True)

    def handle_packet(self):
        for p in self.forwarder.in_queue:
            if random.randint(1,3) == 1:            #change checksum
                p.checksum = 1010
            elif random.randint(1,3) == 2:          #change data
                p.data = 'nonsense data'
            elif random.randint(1,3) == 3:          #change type
                p.msg_type = 'otherType'
            self.forwarder.out_queue.append(p)
        # empty out the in_queue
        self.forwarder.in_queue = []