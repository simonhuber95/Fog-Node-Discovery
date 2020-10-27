import simpy
from simpy import Resource
import random
from vivaldi.vivaldiposition import VivaldiPosition


class FogNode(object):
    def __init__(self, env, id, discovery_protocol, slots, phy_x=4632239.86, phy_y=5826584.42, verbose=True):
        self.env = env
        self.id = id
        self.discovery_protocol = discovery_protocol
        self.resource = Resource(env, 1 if slots < 1 else slots)
        self.msg_pipe = simpy.Store(env)
        self.probe_event = env.event()
        self.phy_x = phy_x
        self.phy_y = phy_y
        self.connect_event = env.event()
        self.in_msg_history = []
        self.out_msg_history = []
        self.verbose = verbose
        self.vivaldiposition = VivaldiPosition.create()

        # Start the run process everytime an instance is created.

        self.connect_process = env.process(self.connect())
        self.closest_node_process = env.process(self.get_closest_node())
        self.probe_network_process = env.process(self.probe_network())
        if self.verbose:
            print("Fog Node {} active at x:{}, y: {}".format(
                self.id, self.phy_x, self.phy_y))

    def connect(self):
        while True:
            in_msg = yield self.msg_pipe.get()
            self.in_msg_history.append(in_msg)
            # waiting the given latency
            yield self.env.timeout(in_msg["latency"])
            if self.verbose:
                print("Node {}: Message type {} from {} at {} from {}: {}".format(
                    self.id, in_msg["msg_type"], in_msg["send_id"], self.env.now, in_msg["timestamp"], in_msg["msg"]))

            if(in_msg["msg_type"] == 1):
                out_msg = self.env.send_message(
                    self.id, in_msg["send_id"], "Reply from node", msg_id=in_msg["msg_id"])
                self.out_msg_history.append(out_msg)

            # Message type 2 = Node Request -> Trigger search for closest node via event
            elif(in_msg["msg_type"] == 2):
                self.probe_event.succeed(in_msg)
                self.probe_event = self.env.event()

            # Message type 3 = Network Probing -> update VivaldiPosition at response or respond at Request
            elif(in_msg["msg_type"] == 3):
                msg_id = in_msg["msg_id"]
                prev_msg = next(
                    (message for message in self.out_msg_history if message["msg_id"] == msg_id), None)
                # If there already exists a message with this ID it is a response and vivaldiposition is updated
                if(prev_msg):
                    sender = self.env.get_participant(in_msg["send_id"])
                    cj = sender.get_vivaldi_position()
                    ej = cj.getErrorEstimate()
                    rtt = self.calculate_rtt(in_msg)

                    try:
                        self.vivaldiposition.update(rtt, cj, ej)
                    except ValueError as e:
                        print(in_msg["send_id"], prev_msg["send_id"])
                        print(
                            "Node {} TypeError at update VivaldiPosition: {}".format(self.id, e))

                # If there is no message with this ID it is a Request and node simply answers
                else:
                    out_msg = self.env.send_message(
                        self.id, in_msg["send_id"], "Probe reply from Node", msg_id=in_msg["msg_id"], msg_type=3)
                    self.out_msg_history.append(out_msg)
            # unknown message type
            else:
                if self.verbose:
                    print("Node {} received unknown message type: {}".format(
                        self.id, in_msg["msg_type"]))

    def get_closest_node(self):
        while True:
            in_msg = yield self.probe_event
            # Closest Node Discovery to be implemented here
            closest_node_id = self.env.get_random_node()
            client_id = in_msg["send_id"]
            msg_id = in_msg["msg_id"]
            self.env.send_message(self.id, client_id,
                                  closest_node_id, msg_type=2, msg_id=msg_id)

    def probe_network(self):
        self.neighbours = self.env.get_neighbours(self)
        while(True):
            # Search for random node, which is not self
            if random.randrange(100) < 50:
                while(True):
                    probe_node = self.env.get_random_node()
                    if(probe_node != self.id):
                        break
            else:
                probe_node = random.choice(self.neighbours)["id"]
            out_msg = self.env.send_message(
                self.id, probe_node, "Probing network", msg_type=3)
            self.out_msg_history.append(out_msg)
            yield self.env.timeout(random.randint(1, 5))

    def get_coordinates(self):
        return self.phy_x, self.phy_y

    def get_vivaldi_position(self):
        return self.vivaldiposition

    def calculate_rtt(self, in_msg):
        msg_id = in_msg["msg_id"]
        out_msg = next(
            (message for message in self.out_msg_history if message["msg_id"] == msg_id), None)
        rtt = in_msg["timestamp"] - out_msg["timestamp"]
        return rtt
