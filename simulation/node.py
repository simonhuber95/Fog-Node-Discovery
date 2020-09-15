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
        # self.closest_node_process = env.process(self.get_closest_node())
        print("Fog Node {} active".format(self.id))


    def connect(self):
        while True:
            msg = yield self.msg_pipe.get()
            # waiting the given latency
            yield self.env.timeout(msg["latency"])
            print("Node {}: Message from client {} at {} from {}: {}".format(self.id, msg["send_id"], self.env.now, msg["timestamp"], msg["msg"]))
            self.env.sendMessage(self.id, msg["send_id"], "Node {} answered".format(self.id))

    # returns closest node relative to client
    def get_closest_node(self):
        while True:
            req = yield self.probe_event
            msg_pipe = req["msg_pipe"]
            msg_pipe.put("test")
            print("Node {}: Looking for nearest node".format(self.id))
      
