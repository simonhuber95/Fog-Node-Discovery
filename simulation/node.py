import simpy
from simpy import Resource
import random


class FogNode(object):
    def __init__(self, env, id, discovery_protocol, slots):
        self.env = env
        self.id = id
        self.discovery_protocol = discovery_protocol
        self.resource = Resource(env, slots)
        self.msg_pipe = simpy.Store(env)
        self.probe_event = env.event()
        self.connect_event = env.event()

        # Start the run process everytime an instance is created.
 
        self.connect_process = env.process(self.connect())
        self.closest_node_process = env.process(self.get_closest_node())
        print("Fog Node {} active".format(self.id))


    def connect(self):
        while True:
            msg = yield self.msg_pipe.get()
            # waiting the given latency
            yield self.env.timeout(msg["latency"])
            print("Node {}: Message type {} from client {} at {} from {}: {}".format(self.id, msg["msg_type"], msg["send_id"], self.env.now, msg["timestamp"], msg["msg"]))
            # Message type 2 = Node Request -> Trigger search for closest node via event 
            if(msg["msg_type"] == 2):
                self.probe_event.succeed(msg["send_id"])
                self.probe_event = self.env.event()
            else:
                self.env.sendMessage(self.id, msg["send_id"], "Reply from node")

    # returns closest node relative to client
    def get_closest_node(self):
        while True:
            client_id = yield self.probe_event
            # Closest Node Discovery to be implemented here
            closest_node_id = self.env.getRandomNode()
            self.env.sendMessage(self.id, client_id, closest_node_id)
      
