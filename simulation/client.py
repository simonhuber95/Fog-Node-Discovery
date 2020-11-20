import math
from random import Random
import simpy
import random
import geopandas
from geopy import distance as geo_distance
from .reconnection_rules import ReconnectionRules
from vivaldi.vivaldiposition import VivaldiPosition
import time
import numpy as np


class MobileClient(object):
    def __init__(self, env, id, plan, discovery_protocol, latency_threshold=0.9, roundtrip_threshold=1.2, timeout_threshold=2, verbose=True):
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
        self.verbose = verbose
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
        if self.verbose:
            print("Client {}: active, current location x: {}, y: {}".format(
                self.id, self.phy_x, self.phy_y))
        # Starting the operating processes
        self.out_process = self.env.process(self.out_connect())
        self.in_process = self.env.process(self.in_connect())
        self.move_process = self.env.process(self.move())
        self.monitor_process = self.env.process(self.monitor())
        self.stop_event = env.event()

        # Init the virtual Position
        self.virtual_position = self.init_virtual_position(discovery_protocol)
        self.discovery_protocol = discovery_protocol
        # Gossip of all nodes
        self.gossip = [
            {"id": self.id, "position": self.get_virtual_position(), "timestamp": env.now, "type": type(self).__name__}]
        self.move_performance = np.nan
        self.out_performance = np.nan
        self.in_performance = np.nan

    def move(self):
        if self.verbose:
            print("Client {}: starting move Process".format(self.id))
        # Iterate through every leg & activity in seperate process
        for activity, leg in self.pairs:
            entry = self.get_entry_from_data(activity=activity, leg=leg)
            duration = entry['trav_time']
            # distance = entry['distance']
            to_x = entry['x']
            to_y = entry['y']
            # skip this leg, if the duration is 0
            if(duration < 1):
                continue

            dist_x = to_x - self.phy_x
            dist_y = to_y - self.phy_y
            vel_x = dist_x / duration
            vel_y = dist_y / duration
            # Moving until x and y match the end point of the leg
            while(round(to_x, 2) != round(self.phy_x, 2) and round(to_y, 2) != round(self.phy_y, 2)):
                start = time.perf_counter()
                self.phy_x += vel_x
                self.phy_y += vel_y
                # Stop Client if it steps out of bounds
                if not self.in_bounds():
                    self.stop_event.succeed("Out of geographical bounds")
                    self.stop_event = self.env.event()
                try:
                    yield self.env.timeout(1)
                except simpy.Interrupt:
                    return

                self.move_performance = time.perf_counter() - start

    def out_connect(self):
        """The process which handles outgoing messages
        If no node is registered or the connection is not valid anymore (see ReconnectionRules), the client sends a type 2 Message to a node
        else the client sends a task to the closest node

        Yields:
            simpy.timeout: Timeout event 
        """
        my_random = Random(self.id)

        while (True):
            start = time.perf_counter()
            # If no node is registered or connection not valid, trigger the event to search for the closest node
            if(not self.closest_node_id or not self.connection_valid()):
                if self.verbose:
                    print("Client {}: Probing network".format(self.id))
                # TODO rather take closest Node from gossip
                random_node = self.env.get_random_node()
                out_msg = self.env.send_message(self.id, random_node,
                                                "Request Closest node", gossip=self.gossip, msg_type=2)
                self.out_msg_history.append(out_msg)
            # If closest node is registered, send messages to node
            else:
                out_msg = self.env.send_message(
                    self.id, self.closest_node_id, "Client {} sends a task".format(self.id), gossip=self.gossip)
                self.out_msg_history.append(out_msg)
            try:
                yield self.env.timeout(my_random.randint(1, 3))
            except simpy.Interrupt:
                return
            self.out_performance = time.perf_counter() - start

    def in_connect(self):
        """The process which handles the incoming messages.
        Updates Gossip, updates the virtual position and depending on the message type performs different actions
        Type 1: Standard answer from node -> do nothin
        Type 2: Response to closest node request -> set closest_node_id to body of the answer

        Yields:
            simypy.Store: incoming Message pipe of the cleint
        """
        while(True):
            try:
                in_msg = yield self.msg_pipe.get()
            except simpy.Interrupt:
                return
            start = time.perf_counter()
            # Save timestamp of reception in message object
            in_msg.rec_timestamp = self.env.now
            # Append message to history
            self.in_msg_history.append(in_msg)

            # Update gossip
            self.update_gossip(in_msg)

            # Updating the virtual Position for every incoming message which is a response in the following
            # Checking if incoming message is a response on which a rtt can be calculated and virtual position is updated
            if(in_msg.prev_msg_id):
                self.update_virtual_position(in_msg)
            # Extracting message Type
            msg_type = in_msg.msg_type

            # Standard task message
            if(msg_type == 1):
                if self.verbose:
                    print("Client {}: Message from Node {} at {} from {}: {}".format(
                        self.id, in_msg.send_id, round(self.env.now, 2), round(in_msg.timestamp, 2), in_msg.body))

            # Closest node message
            elif(msg_type == 2):
                if self.verbose:
                    print("Client {}: Message from Node {} at {} from {}: Closest node is {}".format(
                        self.id, in_msg.send_id, round(self.env.now, 2), round(in_msg.timestamp, 2), in_msg.body))
                self.closest_node_id = in_msg.body

            # Network probing performed by a node
            elif(msg_type == 3):
                if self.verbose:
                    print("Client {}: Message from Node {} at {} from {}: {}".format(
                        self.id, in_msg.send_id, round(self.env.now, 2), round(in_msg.timestamp, 2), in_msg.body))
                out_msg = self.env.send_message(
                    self.id, in_msg.send_id, "Client {} response to ping".format(self.id), gossip=self.gossip, msg_type = 3)
                self.out_msg_history.append(out_msg)

            self.in_performance = time.perf_counter() - start

    def monitor(self):
        """Monitor process for the client.
        Invokes the stop method if the stop event is called

        Yields:
            simpy.Event: Stop event called with a cause
        """
        cause = yield self.stop_event
        self.stop(cause)

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
        # Computing the travel time in seconds
        entry['trav_time'] = sum(
            x * int(t) for x, t in zip([3600, 60, 1], duration.split(":")))
        # Setting the distance as float in meters
        entry['distance'] = float(route.attrib['distance'])
        return entry

    def in_bounds(self):
        """Checks if the Client is in bounds of the simulation

        Returns:
            boolean: Whether or not the client is in bounds
        """
        (x_lower, x_upper, y_lower, y_upper) = self.env.boundaries
        if(x_lower < self.phy_x < x_upper and y_lower < self.phy_y < y_upper):
            return True
        else:
            return False

    def stop(self, cause):
        """Stops all client processes, should only be invoked by the monitor process

        Args:
            cause (string): Description of the cause, that made the client stop
        """
        if(self.out_process.is_alive):
            self.out_process.interrupt(cause)
        if(self.in_process.is_alive):
            self.in_process.interrupt(cause)
        if(self.move_process.is_alive):
            self.move_process.interrupt(cause)
        if(self.verbose):
            print("Client {} stopped: {}".format(self.id, cause))
        # self.move_process.fail(exception=Exception)

    def init_virtual_position(self, discovery_protocol):
        """Inits the virtual position depending on the discovery protocol

        Args:
            discovery_protocol (string): the used discovery protocol

        Returns:
            other: the virtual position for the client
        """
        if discovery_protocol == "vivaldi":
            return VivaldiPosition.create()
        else:
            return None

    def get_virtual_position(self):
        """Returns the virtual position

        Returns:
            other: the virtual position of the node
        """
        return self.virtual_position

    def update_virtual_position(self, in_msg):
        """Wrapper function to update the virtual position. Checks which protocol is currently used and updates the respective virtual coordinate

        Args:
            in_msg (Message)): The incoming Message on which the virtual position is updated
        """
        sender = self.env.get_participant(in_msg.send_id)
        if self.discovery_protocol == "vivaldi":
            cj = sender.get_virtual_position()
            ej = cj.getErrorEstimate()
            rtt = self.calculate_rtt(in_msg)

            try:
                self.virtual_position.update(rtt, cj, ej)
            except ValueError as e:
                print(
                    "Node {} TypeError at update VivaldiPosition: {}".format(self.id, e))

    def calculate_rtt(self, in_msg):
        """Calculates the round-trip-time (rtt) of the incoming message by comparing timestamps with the out message

        Args:
            in_msg (dict): Incoming message

        Returns:
            float: roundtrip time of the message
        """
        msg_id = in_msg.id
        out_msg = next(
            (message for message in self.out_msg_history if message.id == in_msg.prev_msg_id), None)
        rtt = self.env.now - out_msg.timestamp
        return rtt

    def get_coordinates(self):
        """Returns the physical coordinates of the client

        Returns:
            float: x coordinate of the node in GK4/EPSG:31468
            float: y coordinate of the node in GK4/EPSG:31468
        """
        return self.phy_x, self.phy_y

    def update_gossip(self, in_msg):
        """Updates the own gossip with the gossip from the in message

        Args:
            in_msg (list[dict]): An incoming message from another participant
        """
        in_gossip = in_msg.gossip
        for news in in_gossip:
            # If the node is not in own gossip add it
            if not any(entry.get("id") == news["id"] for entry in self.gossip):
                self.gossip.append(news)
            # Update own gossip if the news is newer than own news
            else:
                #own_news = (entry.get("id") == news["id"] for entry in self.gossip)
                own_news = next(
                    (entry for entry in self.gossip if entry["id"] == news["id"]), None)
                # keep own gossip up to date
                if news["id"] == self.id:
                    own_news.update(
                        {"position": self.get_virtual_position(), "timestamp": self.env.now})
                elif own_news["timestamp"] < news["timestamp"]:
                    own_news.update(
                        {"position": self.get_virtual_position(), "timestamp": self.env.now})
