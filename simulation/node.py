from simpy import Resource

class FogNode(object):
    def __init__(self, env, id, discovery_protocol, network, slots):
        self.env = env
        self.id = id
        self.discovery_protocol = discovery_protocol
        self.network = network
        self.resource = Resource(env, slots)
        
        # Start the run process everytime an instance is created.
        self.action = env.process(self.run())
        print("Mobile client {} active, current location x: {}, y: {}".format(self.id, self.phy_x, self.phy_y))

    def run(self):
        while True:
            print('I am a fog node')
            yield self.env.timeout(5)
            
    def connect(self, client):
        with self.resource.request as req:
            yield req
            yield self.env.timeout(1)
            
    # returns closest node relative to client
    def get_closest(self, client):
        # ToDo
        print("Closest node is {}")