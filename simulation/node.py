import simpy
from simpy import Resource
import random
from operator import itemgetter
from vivaldi.vivaldiposition import VivaldiPosition
from .client import MobileClient
from meridian.meridian import Meridian
import math
import time
from random import Random
import numpy as np


class FogNode(object):
    def __init__(self, env, id, discovery_protocol, slots, hardware=2, phy_x=4632239.86, phy_y=5826584.42, verbose=True):
        """Fog Node of the simulation

        Args:
            env (FogEnvironment): Fog Environment of the simulation
            id (uuid): ID of the Fog Node
            discovery_protocol (str): Discovery protocol to be used in the simulation
            slots (int): Amount of slots the node has
            hardware (int, optional): Hardware type of the Fog Node, the lower the better. Defaults to 2.
            phy_x (float, optional): Physical x-coordinate of the Fog Node. Defaults to 4632239.86.
            phy_y (float, optional): Physical y-coordinate of the Fog Node. Defaults to 5826584.42.
            verbose (bool, optional): Verbosity of the Fog Node. Defaults to True.
        """
        self.env = env
        self.id = id
        self.discovery_protocol = discovery_protocol
        self.slots = max(1, slots)
        self.hardware = hardware
        self.clients = []  # {'id', 'timestamp'}
        self.msg_pipe = simpy.Store(env)
        self.phy_x = phy_x
        self.phy_y = phy_y
        self.in_msg_history = []
        self.out_msg_history = []
        self.verbose = verbose
        self.virtual_position = self.init_virtual_position(discovery_protocol)
        # List of all the node of the targets ring with their answers
        self.meridian_requests = []
        # List of all targets the node is currently pinging
        self.meridian_pings = []
        self.gossip = [{"id": self.id, "position": self.virtual_position,
                        "timestamp": env.now, "type": type(self).__name__, "available_slots": self.slots}]

        # Performance measures
        self.probe_performance = np.nan
        self.connect_performance = np.nan
        self.discovery_performance = np.nan
        self.await_performance = np.nan
        self.workload = []

        # Start the processes
        if(discovery_protocol == "vivaldi" or discovery_protocol == "baseline" or discovery_protocol == "random"):
            self.connect_process = env.process(self.vivaldi_connect())
        elif(discovery_protocol == "meridian"):
            self.connect_process = env.process(self.meridian_connect())
            self.ring_management = env.process(
                self.meridian_ring_management(10))
        self.probe_network_process = env.process(self.probe_network())
        self.monitor_process = env.process(self.monitor())
        if self.verbose:
            print("Fog Node {} active at x:{}, y: {}".format(
                self.id, self.phy_x, self.phy_y))

    def vivaldi_connect(self):
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
                print("Node {}: {}".format(self.id, in_msg))
            # Update gossip
            self.update_gossip(in_msg)

            # Message type 1 = Regular Message from client
            if(in_msg.msg_type == 1):
                # check if client is a current client
                current_client = next(
                    (client for client in self.clients if client.get('id') == in_msg.send_id), None)
                # Update if client is already registered
                if current_client:
                    current_client.update({'timestamp': self.env.now})
                # Append to list if client is not already registered
                elif len(self.clients) < self.slots:
                    self.clients.append(
                        {'id': in_msg.send_id, 'timestamp': self.env.now})
                # if we have no capacity for the client we simply do not answer
                else:
                    continue
                
                out_msg = self.env.send_message(
                    self.id, in_msg.send_id, "Reply from node", gossip=self.gossip, response=True, msg_type=1, prev_msg=in_msg)
                self.out_msg_history.append(out_msg)

            # Message type 2 = Node Request -> Trigger search for closest node
            elif(in_msg.msg_type == 2):
                self.vivaldi_get_closest_node(in_msg)

            # Message type 3 = Network Probing -> update VivaldiPosition at response or respond at Request
            elif(in_msg.msg_type == 3):
                # If is a response from a node the virtual position is updated
                if(in_msg.response):
                    self.update_virtual_position(in_msg)

                # If it is a request we simply answer
                else:
                    out_msg = self.env.send_message(
                        self.id, in_msg.send_id, "Probe reply from Node", gossip=self.gossip, response=True, prev_msg=in_msg, msg_type=3)
                    self.out_msg_history.append(out_msg)

            # unknown message type
            else:
                if self.verbose:
                    print("Node {} received unknown message type: {}".format(
                        self.id, in_msg.msg_type))

    def vivaldi_get_closest_node(self, in_msg):
        """Retrieves the closest node from the network for the requesting client. Decision is based on the given discovery protocol:
        baseline: the optimal discovery as a baseline 
        vivaldi: discovery via the vivaldi virtual coordinates
        """
        client = self.env.get_participant(in_msg.send_id)
        # Calculating the closest node based on the omniscient environment.
        # Should not be used for realisitic measurements but as a baseline to compare other protocols to
        if (self.discovery_protocol == "baseline"):
            closest_node_id = self.env.get_closest_node(client.id)
            
        if (self.discovery_protocol == "random"):
            closest_node_id = self.env.get_random_node()

        # Calculating the closest node based on the vivaldi virtual coordinates
        elif(self.discovery_protocol == "vivaldi"):
            estimates = []
            for node in filter(lambda x: x.get('type') == type(self).__name__ and x.get("available_slots") > 0, self.gossip):
                cj = node.get("position")
                est_rtt = cj.estimateRTT(client.get_virtual_position())
                estimates.append({"id": node.get('id'), "rtt": est_rtt})
            sorted_estimates = sorted(estimates, key=itemgetter('rtt'))
            if sorted_estimates:
                closest_node_id = sorted_estimates[0]["id"]
            else:
                closest_node_id = None

        # send message containing the closest node
        client_id = in_msg.send_id
        start = time.perf_counter()
        msg = self.env.send_message(self.id, client_id,
                                    closest_node_id, gossip=self.gossip, msg_type=2, response=True, prev_msg=in_msg)
        self.out_msg_history.append(msg)
        self.discovery_performance = time.perf_counter() - start

    def meridian_connect(self):
        """The connect process of the node with the meridian protocol.
        Waits for a new message to come in and distinguishes between the message types
        Type 1: Regular task message from client, node simply responses
        Type 2: Clostest node request from client, node triggers the probe event to discover closest node asynchronously
        Type 3: Probing response or request from other node, at response the own VivaldiPosition is updated, at request, a response is sent
        Type 4: Ping Request from other node, to ping the target in the recursive nearest node search
        Yields:
            simpy.Event: the incoming message in msg_pipe
            simpy.Event: the latency as a timeout
        """
        while True:
            in_msg = yield self.msg_pipe.get()
            start = time.perf_counter()
            self.in_msg_history.append(in_msg)

            if(in_msg.send_id == self.id):
                print("I received a message from myself: ", in_msg)
                continue

            sender = self.env.get_participant(in_msg.send_id)
            if self.verbose:
                print("Node {}: {}".format(self.id, in_msg))
            # Update gossip
            self.update_gossip(in_msg)
            # Update Meridian if the sender is a fog Node
            if(isinstance(sender, FogNode)):
                self.update_virtual_position(in_msg)

            # Message type 1 = Regular Message from client
            if(in_msg.msg_type == 1):
                # check if client is a current client
                current_client = next(
                    (client for client in self.clients if client.get('id') == in_msg.send_id), None)
                # Update if client is already registered
                if current_client:
                    current_client.update({'timestamp': self.env.now})
                # Append to list if client is not already registered
                elif len(self.clients) < self.slots:
                    self.clients.append(
                        {'id': in_msg.send_id, 'timestamp': self.env.now})
                # if we have no capacity for the client we simply do not answer
                else:
                    continue
                out_msg = self.env.send_message(
                    self.id, in_msg.send_id, "Reply from node", gossip=self.gossip, response=True, prev_msg=in_msg, msg_type=1)
                self.out_msg_history.append(out_msg)

            # Message type 2 = Node Request -> Trigger search for closest node
            elif(in_msg.msg_type == 2):
                self.meridian_get_closest_node(in_msg)

            # Message type 3 = Network Probing -> update VivaldiPosition at response or respond at Request
            elif(in_msg.msg_type == 3):
                # If it is an incoming ping from a Fog Node, just reply
                if(isinstance(sender, FogNode) and not in_msg.prev_msg):
                    out_msg = self.env.send_message(
                        self.id, in_msg.send_id, "Probe reply from Node", gossip=self.gossip, response=True, prev_msg=in_msg, msg_type=3)
                    self.out_msg_history.append(out_msg)

                # If it is an outgoing ping from Client look up the requester and forward the latency to the requester
                elif(isinstance(sender, MobileClient)):
                    meridian_ping = next((ping for ping in self.meridian_pings if ping.get(
                        'target') == in_msg.send_id), None)
                    requester = meridian_ping.get('requester')
                    msg_body = {'latency': in_msg.latency,
                                'target': in_msg.send_id}
                    out_msg = self.env.send_message(
                        self.id, requester, msg=msg_body, gossip=self.gossip, response=True, prev_msg=meridian_ping.get('msg'), msg_type=4)
                    self.out_msg_history.append(out_msg)
                    # Remove the ping information as it is no longer needed
                    self.meridian_pings.remove(meridian_ping)

            # Ping Request from other node, to ping the target
            elif(in_msg.msg_type == 4):
                # Answer from node with ping information to target
                if(in_msg.response):
                    target = in_msg.body.get('target')
                    d_latency = in_msg.body.get('latency')
                    request = next((request for request in self.meridian_requests if request.get(
                        'target') == target), None)
                    if request:
                        request.get('measures').append(
                            {'latency': d_latency, 'member': in_msg.send_id})

                # Only take part in the probing process to a client if node still has the resscource for it
                # By doing this we ensure no more clients are forwarded to this node
                elif len(self.clients) < self.slots:
                    # Append ping information to short memory
                    target = in_msg.body.get('target')
                    self.meridian_pings.append(
                        {'msg_id': in_msg.id, 'requester': in_msg.send_id, 'target': target})
                    out_msg = self.env.send_message(
                        self.id, in_msg.body.get('target'), msg="Ping from Node", gossip=self.gossip, msg_type=3)
                    self.out_msg_history.append(out_msg)

            else:
                if self.verbose:
                    print("Node {} received unknown message type: {}".format(
                        self.id, in_msg.msg_type))

            self.connect_performance = time.perf_counter() - start

    def meridian_get_closest_node(self, in_msg):
        """Triggers the recursive closest node search of the Meridian system

        Args:
            in_msg (Message): The request of the client
        """
        start = time.perf_counter()
        sender = self.env.get_participant(in_msg.send_id)
        # If sender of the Message is another node we iniatiate the search process with the targets last ping
        if(isinstance(sender, FogNode)):
            target = in_msg.body
            # reversing in_msg_history to automatically find the newest ping
            rev_msg_history = reversed(self.in_msg_history)
            ping_from_target = next(
                (message for message in rev_msg_history if message.send_id == target and message.msg_type == 3), None)
            orig_msg = in_msg.prev_msg
            # If there is no ping from the target something logically went wrong and we return
            if not ping_from_target:
                return
            target_latency = ping_from_target.latency

        # If the sender of the message is a client, the target is the sender
        if(isinstance(sender, MobileClient)):
            target = in_msg.send_id
            target_latency = in_msg.latency
            orig_msg = in_msg

        ring_set = self.virtual_position.ring_set
        # Get ring number of the client
        ring_number = ring_set.get_ring_number(target_latency)
        ring = ring_set.get_ring(True, ring_number)
        # Message every member of the same ring as the client with a type 4 message: Ping request to target
        for member in ring.get('members'):
            if(member.get('id') != self.id):
                msg = self.env.send_message(self.id, member.get('id'),
                                      {'latency': target_latency, 'target': target}, gossip=self.gossip, msg_type=4)
                self.out_msg_history.append(msg)
        # Start meridian waiting process to collect answers
        self.meridian_requests.append({'target': target, 'measures': []})
        self.env.process(self.await_meridian_pings(
            target, in_msg.latency, orig_msg))
        self.discovery_performance = time.perf_counter() - start

    def await_meridian_pings(self, target, d_latency, orig_msg):
        """The node has issued other nodes to ping the target.
        Like elaborated in the meridian paper we wait (2*beta + 1)*d timesteps until we forward the best node to the target
        Nodes with no slots available simply do not answer and therefore are ignored in this process

        Args:
            target (target_id): ID of the target, usually a client
            d_latency (float): latency to the target
            orig_msg (Message): original message from the closest node request

        Yields:
            simpy.events.timeout: Waiting the given time
        """
        waiting_time = (2*self.virtual_position.beta + 1)*d_latency
        yield self.env.timeout((waiting_time))
        start = time.perf_counter()
        requests = next(
            (req for req in self.meridian_requests if req.get('target') == target), None)
        if(requests.get('measures')):
            measures = requests.get('measures')
            best_node = min(measures, key=lambda x: x['latency'])
            best_node_id = best_node.get('member')
            msg = self.env.send_message(
                self.id, best_node_id, msg=target, gossip=self.gossip, msg_type=2, prev_msg=orig_msg)
        else:
            msg = self.env.send_message(self.id, target,
                                        self.id, gossip=self.gossip, response=True, msg_type=2, prev_msg=orig_msg)
        self.out_msg_history.append(msg)
        self.meridian_requests.remove(requests)
        self.await_performance = time.perf_counter() - start

    def meridian_ring_management(self, period=30):
        """Meridian ring management process
        Assigns ring membership periodically

        Args:
            period (int, optional): Management period. Defaults to 30.

        """
        # Startup timeout is random so nodes do the ring management at different timesteps
        yield self.env.timeout(Random().randint(10, 20) + Random().random())
        while True:
            self.virtual_position.perform_ring_management()
            yield self.env.timeout(period)

    def probe_network(self):
        """Probing process to continually update the virtual position

        Yields:
            simpy.Event.timeout: timeout event which decides the probing interval
        """
        my_random = Random(self.id)
        yield self.env.timeout(my_random.randint(1,1000)/1000)
        # Initially probe every node in the network once. Is needed for meridian and cannot harm other protocols either
        for node in self.env.nodes:
            probe_node = node.get('id')
            # We dont want to send messages to ourself
            if probe_node != self.id:
                out_msg = self.env.send_message(
                    self.id, probe_node, "Probing network at start", gossip=self.gossip, response=False, msg_type=3)
                self.out_msg_history.append(out_msg)

        self.neighbours = self.env.get_neighbours(self)
        while(True):
            # Search for random node, which is not self as proposed by Dabek et al at 50% of the time, otherwise probe neighbourhood
            if my_random.randint(1, 100) < 50:
                while(True):
                    probe_node = self.env.get_random_node()
                    if(probe_node != self.id):
                        break
            else:
                probe_node = random.choice(self.neighbours)["id"]
            out_msg = self.env.send_message(
                self.id, probe_node, "Probing network", gossip=self.gossip, response=False, msg_type=3)
            self.out_msg_history.append(out_msg)
            # unnecessary complex timeout for the probing process
            # idea is the longer the newtork is established the less probes are necessary
            # Randomness is to avoid all nodes to probe at the exact same moment
            timeout = math.log(
                self.env.now + 1) if math.log(self.env.now + 1) < 2 else 2
            yield self.env.timeout(timeout + my_random.random())

    def monitor(self):
        """Monitor process of the Fog Node
        Manages the available slots and tracks metrics
        """
        while True:
            # check every second if a client connection is outdated
            for client in self.clients:
                if self.env.now - client.get('timestamp') > 2:
                    self.clients.remove(client)
                
            # append current workload to list
            self.workload.append({'timestamp': np.ceil(self.env.now), 'clients': len(self.clients), 'workload': len(self.clients)/self.slots})
            yield self.env.timeout(1)
            
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

    def get_bandwidth(self):
        """Calculates the current bandwith of the node depending on the amount of active connections and total amound of slots available
        Bandwidth is reduced linearly the more Clients are connected

        Returns:
            float: Bandwidth in Gbps between [sla, 1]
        """
        sla = 0.05
        return min(1, max(sla, 1 - (1-sla)* (len(self.clients)/(self.slots))))

    def calculate_rtt(self, in_msg):
        """Calculates the round-trip-time (rtt) of the incoming message by comparing timestamps with the out message

        Args:
            in_msg (dict): Incoming message

        Returns:
            float: roundtrip time of the message
        """
        out_msg = next(
            (message for message in self.out_msg_history if message.id == in_msg.prev_msg.id), None)
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
            if not any(entry.get("id") == news.get("id") for entry in self.gossip):
                self.gossip.append(news)
            # Otherwise update existing news
            else:
                own_news = next(
                    (entry for entry in self.gossip if entry["id"] == news["id"]), None)
                # keep own gossip up to date
                if news.get("id") == self.id:
                    own_news.update(
                        {"position": self.get_virtual_position(), "timestamp": self.env.now, "available_slots": self.slots - len(self.clients)})
                # Update news if it is older than incoming news
                elif own_news.get("timestamp") < news.get("timestamp"):
                    own_news.update(
                        {"position": news.get("position"), "timestamp": news.get("timestamp"), "available_slots": news.get("available_slots")})
                    if(self.discovery_protocol == "meridian" and news.get('type') == FogNode):
                        self.virtual_position.update_meridian(news)

    def init_virtual_position(self, discovery_protocol):
        """Inits the virtual position depending on the discovery protocol

        Args:
            discovery_protocol (str): Discovery protocol to be used in the simulation

        Returns:
            other: The virtual position of the Fog Node or None
        """
        if discovery_protocol == "baseline":
            return None
        elif discovery_protocol == "vivaldi":
            return VivaldiPosition.create()
        elif discovery_protocol == "meridian":
            return Meridian(self.id, self.env.amount_nodes)

    def update_virtual_position(self, in_msg):
        """Wrapper function to update the virtual position of the Fog Node
        Calls the corresponding update mechanism depending on the discovery protcol

        Args:
            in_msg (Message): Incoming message upon which the virtual position should be updated
        """
        if self.discovery_protocol == "baseline" or self.discovery_protocol == "random":
            return

        sender_news = next(
            (news for news in in_msg.gossip if news.get('id') == in_msg.send_id), None)
        # should not happen but just in case
        if not sender_news:
            print("whooopsies")
            return

        virtual_position = sender_news.get('position')

        if self.discovery_protocol == "vivaldi":
            cj = virtual_position
            ej = cj.getErrorEstimate()
            rtt = self.calculate_rtt(in_msg)

            try:
                self.get_virtual_position().update(rtt, cj, ej)
            except ValueError as e:
                print(
                    "Node {} TypeError at update VivaldiPosition: {}".format(self.id, e))

        elif self.discovery_protocol == "meridian":
            self.virtual_position.add_node(
                in_msg.send_id, in_msg.latency, virtual_position.get_vector())
