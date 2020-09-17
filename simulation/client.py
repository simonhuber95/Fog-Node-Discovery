import math
import simpy
import random
from geopy import distance as geo_distance


class MobileClient(object):
    def __init__(self, env, id, plan):
        self.env = env
        self.id = id
        self.plan = plan
        self.connected = False
        # ID of closest node as string
        self.closest_node = ""
        # Event triggers search for closest node
        self.req_node_event = env.event()
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
        # Starting the operating processes
        self.request_process = self.env.process(self.req_closest_node())
        self.connect_process = self.env.process(self.connect())
        self.move_process = self.env.process(self.move())    
        
    def move(self):
        print("Client {}: starting move Process".format(self.id))
        # Iterate through every leg & activity in seperate process
        for activity, leg in self.pairs:
            entry = self.get_entry_from_data(activity=activity, leg=leg)
            duration = entry['trav_time']
            distance = entry['distance']
            to_x = entry['x']
            to_y = entry['y']

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

                yield self.env.timeout(1)

                # print("Timestep: {} Client id: {} x:{:.2f} y:{:.2f}".format(
                #     self.env.now, self.id, self.phy_x, self.phy_y))
                # print("Delta x: {}, Delta y: {}".format(round(to_x - self.phy_x, 2), round(to_y - self.phy_y, 2)))

    def req_closest_node(self):
        print("Client {}: starting Request closest node Process".format(self.id))
        while(True):
            yield self.req_node_event # passivate the search for closest node. Is triggered if reconnection Criteria is fullfilled
            # Emit Event to any node of the Fog Network to retrieve closest node
            print("Client {}: Probing network".format(self.id))
            random_node = self.env.getRandomNode()
            self.env.sendMessage(self.id, random_node, "Request Closest node", msg_type = 2)
            # Receiving Message from random node
            msg = yield self.msg_pipe.get()
            print("Client {}: Nearest node is {}".format(self.id, msg["msg"]))
            self.closest_node = msg["msg"]

    def connect(self):
        while (True):
            # If no node is registered or connection not valid, trigger the event to search for the closest node
            if(not self.closest_node or not self.connection_valid):
                print("No node registered, trigger node request")
                self.req_node_event.succeed()
                self.req_node_event = self.env.event()
            # If closest node is registered, send messages to node
            else:
                self.env.sendMessage(self.id, self.closest_node, "Client {} sends a task".format(self.id))
                msg = yield self.msg_pipe.get()
                # Waiting the given latency
                yield self.env.timeout(msg["latency"])
                print("Client {}: Message from Node {} at {} from {}: {}".format(self.id, msg["send_id"], round(self.env.now, 2), round(msg["timestamp"], 2), msg["msg"]))
            yield self.env.timeout(random.randint(0,5))
            
            
    def connection_valid(self):
        """
        Checks if the connection to the current Node is Valid 
        Returns boolean if valod or not
        """
        return random.choice([True, False])
        
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
