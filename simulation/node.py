import simpy
from simpy import Resource
import random
from operator import itemgetter
from vivaldi.vivaldiposition import VivaldiPosition
from meridian.meridian import Meridian
import math
import time
from random import Random
import numpy as np


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
        self.virtual_position = self.init_virtual_position(discovery_protocol)
        self.gossip = [{"id": self.id, "position": self.virtual_position,
                        "timestamp": env.now, "type": type(self).__name__}]

        # Performance measures
        self.probe_performance = np.nan
        self.connect_performance = np.nan
        self.discovery_performance = np.nan

        # Start the processes
        self.connect_process = env.process(self.connect())
        self.closest_node_process = env.process(self.get_closest_node())
        self.probe_network_process = env.process(self.probe_network())
        if self.verbose:
            print("Fog Node {} active at x:{}, y: {}".format(
                self.id, self.phy_x, self.phy_y))

    def connect(self):
        """The connect process of the node.
        Waits for a new message to come in and distinguishes between the message types
        Type 1: Regular task message from client, node simply responses
        Type 2: Clostest node request from client, node triggers the probe event to discover closest node asynchronously
        Type 3: Probing response or request from other node, at response the own VivaldiPosition is updated, at request, a response is sent
        Yields:
            simpy.Event: the incoming message in msg_pipe
            simpy.Event: the latency as a timeout
        """
        while True:
            in_msg = yield self.msg_pipe.get()
            self.in_msg_history.append(in_msg)

            if self.verbose:
                print("Node {}: Message type {} from {} at {} from {}: {}".format(
                    self.id, in_msg.msg_type, in_msg.send_id, self.env.now, in_msg.timestamp, in_msg.body))
            # Update gossip
            self.update_gossip(in_msg)

            # Message type 1 = Regular Message from client, just reply
            if(in_msg.msg_type == 1):
                out_msg = self.env.send_message(
                    self.id, in_msg.send_id, "Reply from node", gossip=self.gossip, prev_msg_id=in_msg.id)
                self.out_msg_history.append(out_msg)

            # Message type 2 = Node Request -> Trigger search for closest node via event
            elif(in_msg.msg_type == 2):
                self.probe_event.succeed(in_msg)
                self.probe_event = self.env.event()

            # Message type 3 = Network Probing -> update VivaldiPosition at response or respond at Request
            elif(in_msg.msg_type == 3):
                # If there already exists a message with this ID it is a response and the virtual position is updated
                if(in_msg.prev_msg_id):
                    self.update_virtual_position(in_msg)
                # If there is no message with this ID it is a Request and node simply answers
                else:
                    out_msg = self.env.send_message(
                        self.id, in_msg.send_id, "Probe reply from Node", gossip=self.gossip, prev_msg_id=in_msg.id, msg_type=3)
                    self.out_msg_history.append(out_msg)
            # unknown message type
            else:
                if self.verbose:
                    print("Node {} received unknown message type: {}".format(
                        self.id, in_msg.msg_type))

    def get_closest_node(self):
        """Retrieves the closest node from the network for the requesting client. Decision is based on the given discovery protocol:
        baseline: the optimal discovery as a baseline 
        vivaldi: discovery via the vivaldi virtual coordinates

        Yields:
            simpy.Event: waits for the probe event to be triggered, then searches for the closest node to the client
        """
        while True:
            in_msg = yield self.probe_event

            client = self.env.get_participant(in_msg.send_id)

            # Calculating the closest node based on the omniscient environment.
            # Should not be used for realisitic measurements but as a baseline to compare other protocols to
            if (self.discovery_protocol == "baseline"):
                closest_node_id = self.env.get_closest_node(client.id)

            # Calculating the closest node based on the vivaldi virtual coordinates
            elif(self.discovery_protocol == "vivaldi"):
                estimates = []
                for node in filter(lambda x: x['type'] == type(self).__name__, self.gossip):
                    cj = node["position"]
                    est_rtt = cj.estimateRTT(client.get_virtual_position())
                    estimates.append({"id": node["id"], "rtt": est_rtt})
                sorted_estimates = sorted(estimates, key=itemgetter('rtt'))
                closest_node_id = sorted_estimates[0]["id"]
            
            elif(self.discovery_protocol == "meridian"):
                # TODO
                closest_node_id = self.id
                self.virtual_position.calculate_hypervolume()

            # send message containing the closest node
            client_id = in_msg.send_id
            msg_id = in_msg.id
            start = time.perf_counter()
            msg = self.env.send_message(self.id, client_id,
                                        closest_node_id, gossip=self.gossip, msg_type=2, prev_msg_id=msg_id)
            self.discovery_performance = time.perf_counter() - start

    def probe_network(self):
        """Probing process to continually update the virtual position

        Yields:
            simpy.Event.timeout: timeout event which decides the probing interval
        """
        my_random = Random(self.id)
        self.neighbours = self.env.get_neighbours(self)
        while(True):
            start = time.perf_counter()
            # Search for random node, which is not self as proposed by Dabek et al at 50% of the time, otherwise probe neighbourhood
            if my_random.randrange(100) < 50:
                while(True):
                    probe_node = self.env.get_random_node()
                    if(probe_node != self.id):
                        break
            else:
                probe_node = random.choice(self.neighbours)["id"]
            out_msg = self.env.send_message(
                self.id, probe_node, "Probing network", gossip=self.gossip, msg_type=3)
            self.out_msg_history.append(out_msg)
            # unnecessary complex timeout for the probing process
            # idea is the longer the newtork is established the less probes are necessary
            # Randomness is to avoid all nodes to probe at the exact same moment
            timeout = math.log(
                self.env.now + 1) if math.log(self.env.now + 1) < 2 else 2
            self.probe_performance = time.perf_counter() - start
            yield self.env.timeout(timeout + my_random.random())

    def get_coordinates(self):
        """Returns the physical coordinates of the node

        Returns:
            float: x coordinate of the node in GK4/EPSG:31468
            float: y coordinate of the node in GK4/EPSG:31468
        """
        return self.phy_x, self.phy_y

    def get_virtual_position(self):
        """Returns the virtual position

        Returns:
            other: the virtual position of the node
        """
        return self.virtual_position

    def calculate_rtt(self, in_msg):
        """Calculates the round-trip-time (rtt) of the incoming message by comparing timestamps with the out message

        Args:
            in_msg (dict): Incoming message

        Returns:
            float: roundtrip time of the message
        """
        out_msg = next(
            (message for message in self.out_msg_history if message.id == in_msg.prev_msg_id), None)
        rtt = self.env.now - out_msg.timestamp
        return rtt

    def update_gossip(self, in_msg):
        """Updates the own gossip with the gossip from the in message

        Args:
            in_msg (list[dict]): An incoming message from another participant
        """
        in_gossip = in_msg.gossip
        for news in in_gossip:
            # If the news is not in own gossip add it
            if not any(entry.get("id") == news["id"] for entry in self.gossip):
                self.gossip.append(news)
            # Otherwise update existing news
            else:
                own_news = next(
                    (entry for entry in self.gossip if entry["id"] == news["id"]), None)
                # keep own gossip up to date
                if news["id"] == self.id:
                    own_news.update(
                        {"position": self.get_virtual_position(), "timestamp": self.env.now})
                # Update news if it is older than incoming news
                elif own_news["timestamp"] < news["timestamp"]:
                    own_news.update(
                        {"position": self.get_virtual_position(), "timestamp": self.env.now})

    def init_virtual_position(self, discovery_protocol):
        if discovery_protocol == "baseline":
            return None
        elif discovery_protocol == "vivaldi":
            return VivaldiPosition.create()
        elif discovery_protocol == "meridian":
            return Meridian(self.env.amount_nodes)

    def update_virtual_position(self, in_msg):
        if self.discovery_protocol == "baseline":
            return

        sender = self.env.get_participant(in_msg.send_id)
        if self.discovery_protocol == "vivaldi":
            cj = sender.get_virtual_position()
            ej = cj.getErrorEstimate()
            rtt = self.calculate_rtt(in_msg)

            try:
                self.get_virtual_position().update(rtt, cj, ej)
            except ValueError as e:
                print(
                    "Node {} TypeError at update VivaldiPosition: {}".format(self.id, e))

        elif self.discovery_protocol == "meridian":
            self.virtual_position.add_node(sender.id, in_msg.latency,
                              sender.virtual_position.get_vector())
            
