import simpy
from simpy import Resource
import random


class FogNode(object):
    def __init__(self, env, id, discovery_protocol, slots, phy_x = 4590909.84, phy_y = 5821199.78):
        self.env = env
        self.id = id
        self.discovery_protocol = discovery_protocol
        self.resource = Resource(env, slots)
        self.msg_pipe = simpy.Store(env)
        self.probe_event = env.event()
        self.phy_x = phy_x
        self.phy_y = phy_y
        self.connect_event = env.event()
        self.in_msg_history = []
        self.out_msg_history = []

        # Start the run process everytime an instance is created.
 
        self.connect_process = env.process(self.connect())
        self.closest_node_process = env.process(self.get_closest_node())
        print("Fog Node {} active".format(self.id))


    def connect(self):
        while True:
            in_msg = yield self.msg_pipe.get()
            self.in_msg_history.append(in_msg)
            # waiting the given latency
            yield self.env.timeout(in_msg["latency"])
            print("Node {}: Message type {} from client {} at {} from {}: {}".format(self.id, in_msg["msg_type"], in_msg["send_id"], self.env.now, in_msg["timestamp"], in_msg["msg"]))
            # Message type 2 = Node Request -> Trigger search for closest node via event 
            if(in_msg["msg_type"] == 2):
                self.probe_event.succeed(in_msg)
                self.probe_event = self.env.event()
            else:
                out_msg = self.env.sendMessage(self.id, in_msg["send_id"], "Reply from node", msg_id = in_msg["msg_id"])
                self.out_msg_history.append(out_msg)

    # returns closest node relative to client
    def get_closest_node(self):
        while True:
            in_msg = yield self.probe_event
            # Closest Node Discovery to be implemented here
            closest_node_id = self.env.getRandomNode()
            client_id = in_msg["send_id"]
            msg_id = in_msg["msg_id"]
            self.env.sendMessage(self.id, client_id, closest_node_id, msg_type = 2, msg_id = msg_id)
      
