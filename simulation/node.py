from simpy import Resource


class FogNode(object):
    def __init__(self, env, id, discovery_protocol, slots):
        self.env = env
        self.id = id
        self.discovery_protocol = discovery_protocol
        self.network = network
        self.resource = Resource(env, slots)
        self.probe_event = env.event()
        self.connect_event = env.event()

        # Start the run process everytime an instance is created.
        self.action = env.process(self.run())
        print("Fog Node {} active".format(self.id))

    def run(self):
        while True:
            req = yield self.probe_event
            msg_pipe = req["msg_pipe"]
            msg_pipe.put("test")
            print("Node {}: Looking for nearest node".format(self.id))
            yield self.connect_event
            print("Node {}: Connection to client".format(self.id))
            yield self.env.timeout(1)

    def connect(self, client):
        # with self.resource.request as req:
        #    yield req
        #    yield self.env.timeout(1)
        print("ToDo")

    # returns closest node relative to client
    def get_closest(self, client):
        # ToDo
        print("Closest node is {}")
