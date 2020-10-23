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
                print("Node {}: Message type {} from client {} at {} from {}: {}".format(
                    self.id, in_msg["msg_type"], in_msg["send_id"], self.env.now, in_msg["timestamp"], in_msg["msg"]))
            # Message type 2 = Node Request -> Trigger search for closest node via event
            if(in_msg["msg_type"] == 2):
                self.probe_event.succeed(in_msg)
                self.probe_event = self.env.event()
            else:
                out_msg = self.env.send_message(
                    self.id, in_msg["send_id"], "Reply from node", msg_id=in_msg["msg_id"])
                self.out_msg_history.append(out_msg)

    # returns closest node relative to client
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
            if random.randrange(100) < 50:
                probe_node = self.env.get_random_node()
            else:
                probe_node = random.choice(self.neighbours)["id"]
            out_msg = self.env.send_message(
                self.id, probe_node, "Probing network", type = 3)
            self.out_msg_history.append(out_msg)
            yield self.env.timeout(random.randint(1, 5))

    def get_coordinates(self):
        return self.phy_x, self.phy_y
