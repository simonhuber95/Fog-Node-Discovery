import math
import simpy
import random
from geopy import distance as geo_distance


class MobileClient(object):
    def __init__(self, env, id, plan):
        self.env = env
        self.id = id
        self.plan = plan
        self.network = network
        self.connected = False
        self.msg_pipe = simpy.Store(env)
        # Set coordinates to first activity in plan
        self.phy_x = float(plan.find('activity').attrib["x"])
        self.phy_y = float(plan.find('activity').attrib["y"])
        # Zip all activities and legs into pairs (except for initial activity used for init coordinates)
        self.pairs = zip(plan.findall('activity')[1:], plan.findall('leg'))
        self.virt_x = 0
        self.virt_y = 0
        print("Client {}: active, current location x: {}, y: {}".format(
            self.id, self.phy_x, self.phy_y))
        # Start the run process everytime an instance is created.
        self.action = env.process(self.run())
        self.connected_node = False

    def run(self):
        print("Client {}: starting".format(self.id))
        # Finding closest node process from by connecting to random node
        closest_node = yield self.env.process(self.req_closest_node())
        
        # Connecting to closest node
        yield self.env.process(self.connect(closest_node))
        
        # Iterate through every leg & activity in seperate process
        for activity, leg in self.pairs:
            entry = self.get_entry_from_data(activity=activity, leg=leg)
            print(entry)
            yield self.env.process(self.move(entry['x'], entry['y'], entry['trav_time'], entry['distance']))

    def move(self, to_x, to_y, duration, distance):
        # Calculating the deltas in each direction
        # the order is (latitude, longitude) or (y, x) in Cartesian terms
        # dist_x = geo_distance.distance((0, self.phy_x), (0, to_x))
        # dist_y = geo_distance.distance((self.phy_y, 0), (to_y, 0))
        dist_x = to_x - self.phy_x
        dist_y = to_y - self.phy_y
        vel_x = dist_x / duration
        vel_y = dist_y / duration
        while(round(to_x, 2) != round(self.phy_x, 2) and round(to_y, 2) != round(self.phy_y, 2)):
            self.phy_x += vel_x
            self.phy_y += vel_y

            # if (self.connected_node == False):
            # self.req_closest_node() ToDo
            # print("Client {}: Not connected to network".format(self.id))
            yield self.env.timeout(1)

            # print("Timestep: {} Client id: {} x:{:.2f} y:{:.2f}".format(
            #     self.env.now, self.id, self.phy_x, self.phy_y))
            # print("Delta x: {}, Delta y: {}".format(round(to_x - self.phy_x, 2), round(to_y - self.phy_y, 2)))

    def req_closest_node(self):
        while(not self.connected):
            # Emit Event to any node of the Fog Network to retrieve closest node
            print("Client {}: Probing network".format(self.id))
            node = random.choice(self.network)
            node.probe_event.succeed(
                {"client_id": self.id, "msg_pipe": self.msg_pipe})
            node.probe_event = self.env.event()
            # Receiving Message from radnom node
            in_msg = yield self.msg_pipe.get()
            print("Client {}: Nearest node is {}".format(self.id, in_msg))

    def connect(self, node_id):
        # Connect to closest node of the Fog Network
        print("ToDo")

    def get_entry_from_data(self, activity, leg):
        entry = {}
        # Setting the physical end x coordinate from the following activity
        entry['x'] = float(activity.attrib['x'])
        # Setting the physical end y coordinate from the following activty
        entry['y'] = float(activity.attrib['y'])
        # retrieving the route from the leg node
        route = leg.find('route')
        # Setting the travel time in seconds
        duration = route.attrib['trav_time']
        entry['trav_time'] = sum(
            x * int(t) for x, t in zip([3600, 60, 1], duration.split(":")))
        # Setting the distance as float in meters
        entry['distance'] = float(route.attrib['distance'])
        return entry
