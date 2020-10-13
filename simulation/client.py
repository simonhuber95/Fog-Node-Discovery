import math
import simpy
import random
import geopandas
from geopy import distance as geo_distance
from reconnection_rules import ReconnectionRules


class MobileClient(object):
    def __init__(self, env, id, plan, latency_threshold=0.9, roundtrip_threshold=1.2, timeout_threshold=2):
        """ Initializes a Mobile Client
        Args:
            env (simpy.Environment): The Environment of the simulation
            id (string): The ID of the Client
            plan (XML object): The XML Object of the Client from the open berlin scenario
        """
        self.env = env
        self.id = id
        self.plan = plan
        self.connected = False
        # ID of closest node as string
        self.closest_node_id = ""
        self.latency_threshold = latency_threshold
        self.roundtrip_threshold = roundtrip_threshold
        self.timeout_threshold = timeout_threshold
        # Event triggers search for closest node
        self.req_node_event = env.event()
        self.msg_pipe = simpy.FilterStore(env)
        self.in_msg_history = []
        self.out_msg_history = []
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
        self.out_process = self.env.process(self.out_connect())
        self.in_process = self.env.process(self.in_connect())
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
            if(duration < 1): continue
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

    def out_connect(self):
        while (True):
            # If no node is registered or connection not valid, trigger the event to search for the closest node
            if(not self.closest_node_id or not self.connection_valid()):
                print("Client {}: Probing network".format(self.id))
                random_node = self.env.getRandomNode()
                out_msg = self.env.sendMessage(self.id, random_node,
                                               "Request Closest node", msg_type=2)
                self.out_msg_history.append(out_msg)
            # If closest node is registered, send messages to node
            else:
                out_msg = self.env.sendMessage(
                    self.id, self.closest_node_id, "Client {} sends a task".format(self.id))
                self.out_msg_history.append(out_msg)

            yield self.env.timeout(random.randint(1, 5))

    def in_connect(self):
        while(True):
            msg = yield self.msg_pipe.get()
            # Waiting the given latency
            yield self.env.timeout(msg["latency"])
            # Append message to history
            self.in_msg_history.append(msg)
            # Extracting message Type
            msg_type = msg["msg_type"]
            # Standard task message
            if(msg_type == 1):
                print("Client {}: Message from Node {} at {} from {}: {}".format(
                    self.id, msg["send_id"], round(self.env.now, 2), round(msg["timestamp"], 2), msg["msg"]))
            # Closest node message
            elif(msg_type == 2):
                print("Client {}: Message from Node {} at {} from {}: Closest node is {}".format(
                    self.id, msg["send_id"], round(self.env.now, 2), round(msg["timestamp"], 2), msg["msg"]))
                self.closest_node_id = msg["msg"]

    def connection_valid(self):
        """Checks all rules of the reconnection_rule.py
        Returns:
            boolean: If all the rules are fulfilled and the connection is currently valid
        """
        Rules = ReconnectionRules(self.env)
        check = all([
            Rules.latency_rule(self.id, self.closest_node_id,
                               threshold=self.latency_threshold),
            Rules.roundtrip_rule(
                self.out_msg_history, self.in_msg_history, threshold=self.roundtrip_threshold),
            Rules.timeout_rule(
                self.out_msg_history, self.in_msg_history, threshold=self.roundtrip_threshold)
        ])
        return check

    def get_entry_from_data(self, activity, leg):
        """Extracts a combined entry from a touple of one activity and one leg.

        Args:
            activity (XML Elemenent): The activity element of the open berlin scenario
            leg (XML Element): The leg element prior to the activity of the open berlin scenario

        Returns:
            dict: A dictionary with the fields "x", "y", "route", "trav_time" and "distance"
        """
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
