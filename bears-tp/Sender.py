import sys
import getopt

import Checksum
import BasicSender

'''
This is a skeleton sender class. Create a fantastic transport protocol here.
'''
class Sender(BasicSender.BasicSender):
    def __init__(self, dest, port, filename, debug=False, sackMode=False):
        super(Sender, self).__init__(dest, port, filename, debug)
        if sackMode:
            #raise NotImplementedError #remove this line when you implement SACK
            pass

    # Main sending loop.
    def start(self):
        seqno = 0 # initial sequence number
        msg_type = None # start, data, end
        msg = self.infile.read(1400) # message (data)
        end_pckt_num = None
        packet_dict, pckt_id, sack_lst = {}, [], [] # format: {seqno: [msg, ACK #]}

        while (True):
            # Establishing the handshake.
            if (seqno == 0):
                msg_type = "start"
                packet = self.make_packet(msg_type, seqno, msg)
                self.send(packet)
                response_pckt = self.receive(0.5)
                if (response_pckt != None and Checksum.validate_checksum(response_pckt)):
                    if (sackMode):
                        msg_type = self.split_sack(response_pckt)[0] #sack
                    else:
                        msg_type = self.split_ack(response_pckt)[0] #ack 
                    if (msg_type == 'ack' or msg_type == 'sack'):
                        seqno += 1
                        msg_type = 'data'

            else:
                x = self.populate_dict(packet_dict, seqno, pckt_id, msg_type)
                packet_dict, seqno, end_pckt_num, msg_type = x[0], x[1], x[2], x[3]
                response_pckt = self.receive(0.5)
                if (response_pckt != None):
                    if (sackMode):
                        ack_num = self.split_sack(response_pckt)[1]
                    else:
                        ack_num = self.split_ack(response_pckt)[1]
                    if (end_pckt_num != None and (int(end_pckt_num) == int(ack_num))):
                        break
                if not (sackMode):
                    self.handle_acks(packet_dict, pckt_id, response_pckt, msg_type)
                else:
                    self.handle_sacks(packet_dict, pckt_id, response_pckt, msg_type, sack_lst)

    """ Populates the dictionary with values and returns
        a dictionary, curr seqno"""
    def populate_dict(self, packet_dict, seqno,
                      pckt_id, msg_type):

        if (msg_type != 'end'):
            end_sequence_num = None
            while (len(packet_dict) < 5 and (not (msg_type == 'end'))):
                msg = self.infile.read(1400)
                if (msg == ""):
                    msg_type = 'end'
                    end_sequence_num = seqno + 1
                packet = self.make_packet(msg_type, seqno, msg)
                packet_dict[seqno] = [packet, msg_type, 1]
                pckt_id.append(seqno)
                self.send(packet)
                seqno += 1
            return packet_dict, seqno, end_sequence_num, msg_type
        else:
            return packet_dict, seqno, seqno, msg_type

    """ Split the ack into its parts: msg_type, seqno, checksum
        If the ack is invalid, it returns 'None' """
    def split_ack(self, response_pckt):
        if (response_pckt != None):
            parts = response_pckt.split("|")
            return parts[0], parts[1], parts[2]
        return None

    """ Split the sack into its parts: msg_type, cum_ack, sacks, checksum.
        If the ack is invalid, method returns 'None'"""
    def split_sack(self, response_pckt):
        lst = []
        if (response_pckt != None):
            parts = response_pckt.split('|')
            lst = parts[1].split(';')
            if(len(lst) == 1):
                return parts[0], lst[0], [], parts[2]
            return parts[0], lst[0], [lst[1]], parts[2]
        return None

    """ Either update the dictionary based on the
        ack received or resend the packet."""
    def handle_acks(self, packet_dict, pckt_id, response_packet, msg_type):

        if (response_packet != None and Checksum.validate_checksum(response_packet)):
            response = self.split_ack(response_packet)
            msg_type = response[0]
            ack_seqno = response[1]

            # checks to see if we have a corrupted message type if were are not in sack mode. 
            if (msg_type != 'ack'):
                return 

            # update the number of acks in the packet dictionary for each packet.
            if (ack_seqno in packet_dict.keys()):
                packet_dict[ack_seqno][2] += 1
            
            # Handle duplicate acknowledgements. IF we have 3 acks for the same packet,
            # we should retransmit only that specific packet.
            if (ack_seqno in packet_dict.keys() and packet_dict[ack_seqno][2] >= 4):
                self.retransmitOnlyPacket(packet_dict, ack_seqno)

            # Handle correct ack by deleting the appropriate packets from the window.
            elif (((int(ack_seqno) - int(pckt_id[0])) >= 1) and msg_type != 'end'):
                diff = int(ack_seqno)  - int(pckt_id[0]) # how many elements we should delete from dict/ lst.
                packet_dict, pckt_id = self.delete_elems(diff, pckt_id, packet_dict)

            # if ackqno == lowest packet number, then we have dropped that packet. 
            elif (int(ack_seqno) - int(pckt_id[0]) == 0):
                self.retransmitPackets(packet_dict)
               
        # Handle packet loss and corruption. If the ack is never received, or 
        # the checksum for the ack is invalid, we should retransmit the entire window.
        elif(response_packet == None or (not Checksum.validate_checksum(response_packet))):
            self.retransmitPackets(packet_dict)

    def handle_sacks(self, packet_dict, pckt_id, response_pckt, msg_type, sack_lst):
        if (response_pckt != None and Checksum.validate_checksum(response_pckt)):
            response = self.split_sack(response_pckt)
            msg_type = response[0] # msg_type
            sack_seqno = response[1] # sack seqno
            sack_lst = self.update_sack_lst(response[2], sack_lst) # updates the sack list.

            if (msg_type != 'sack'):
                return

            if (sack_seqno in packet_dict.keys()):
                packet_dict[sack_seqno][2] += 1

            if (sack_seqno in packet_dict.keys() and packet_dict[sack_seqno][2] >= 4):
                self.retransmitOnlyPacket(packet_dict, sack_seqno)

            # Handle correct ack by deleting the appropriate packets from the window.
            elif (((int(sack_seqno) - int(pckt_id[0])) >= 1) and msg_type != 'end'):
                diff = int(sack_seqno)  - int(pckt_id[0]) # how many elements we should delete from dict/ lst.
                packet_dict, pckt_id = self.delete_elems(diff, pckt_id, packet_dict)

            elif (int(sack_seqno) - int(pckt_id[0]) == 0):
                self.retransmitSackPackets(packet_dict, response_pckt, sack_lst)

        elif(response_pckt == None or (not Checksum.validate_checksum(response_pckt))):
            self.retransmitPackets(packet_dict)

    """ Updates the sack lst. """
    def update_sack_lst(self, packets_received, sack_lst):
        for packet in packets_received:
            if (packet not in sack_lst):
                sack_lst.append(packet)
        return sack_lst

    """ Delete DIFF from pckt_id and packet_dict """
    def delete_elems(self, diff, pckt_id, packet_dict, sack_lst = None):
        count = 0
        while (count < diff):
            del packet_dict[pckt_id[0]]
            pckt_id.pop(0)
            count += 1
        return packet_dict, pckt_id

    """ Resend the entire packet window. """
    def retransmitPackets(self, packet_dict):
        for key in packet_dict.keys():
            packet_dict[key][2] = 1 # reset ack number to 1.
            self.send(packet_dict[key][0])

    """ For sack mode, sends the appropriate packets. """
    def retransmitSackPackets(self, packet_dict, response_pckt, sack_lst):
        for key in packet_dict.keys():
            if (key not in sack_lst):
                self.send(packet_dict[key][0])
        return sack_lst

    """ When received 3 acks, just retransmit the that specific packet."""
    def retransmitOnlyPacket(self, packet_dict, ack_seqno):
        packet_dict[ack_seqno][2] = 1 # reset ack number to 1.
        self.send(packet_dict[ack_seqno][0])

    def log(self, msg):
        if self.debug:
            print msg

'''
This will be run if you run this script from the command line. You should not
change any of this; the grader may rely on the behavior here to test your
submission.
'''
if __name__ == "__main__":
    def usage():
        print "BEARS-TP Sender"
        print "-f FILE | --file=FILE The file to transfer; if empty reads from STDIN"
        print "-p PORT | --port=PORT The destination port, defaults to 33122"
        print "-a ADDRESS | --address=ADDRESS The receiver address or hostname, defaults to localhost"
        print "-d | --debug Print debug messages"
        print "-h | --help Print this usage message"
        print "-k | --sack Enable selective acknowledgement mode"

    try:
        opts, args = getopt.getopt(sys.argv[1:],
                               "f:p:a:dk", ["file=", "port=", "address=", "debug=", "sack="])
    except:
        usage()
        exit()

    port = 33122
    dest = "localhost"
    filename = None
    debug = False
    sackMode = False

    for o,a in opts:
        if o in ("-f", "--file="):
            filename = a
        elif o in ("-p", "--port="):
            port = int(a)
        elif o in ("-a", "--address="):
            dest = a
        elif o in ("-d", "--debug="):
            debug = True
        elif o in ("-k", "--sack="):
            sackMode = True

    s = Sender(dest, port, filename, debug, sackMode)
    try:
        s.start()
    except (KeyboardInterrupt, SystemExit):
        exit()
