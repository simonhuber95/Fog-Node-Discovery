from simpy import Environment
import math
import uuid
from random import Random
import random
from operator import itemgetter
from .message import Message
from .client import MobileClient
from .node import FogNode
import time


class FogEnvironment(Environment):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.clients = []
        self.nodes = []
        self.celltowers = []
        self.boundaries = tuple()
        self.messages = []
        self.monitor_process = self.process(self.monitor())

    def get_participant(self, id_x):
        """
        Getter for all participants in the network
        Parameter ID as string
        Returns the participant object for the given ID
        """
        entry = next(
            (elem for elem in [*self.clients, *self.nodes] if elem["id"] == id_x), None)
        if not entry:
            return None
        return entry.get("obj")

    def get_random_node(self):
        """
        Returns ID of random fog node
        """
        return random.choice(self.nodes)["id"]

    def send_message(self, send_id, rec_id, msg, gossip, response=False, msg_type=1, prev_msg=None):
        """
        Parameter send_id as string: ID of sender
        Paramater rec_id as string: ID of recipient
        Parameter msg as string: Message to be send
        Parameter gossip as dict: Gossip of all virtual coordinates
        Parameter msg_type as int *optional: type of message -> 1: regular message (default), 2: Closest node request, 3: Node discovery
        Parameter prev_msg as Message *optional: the predecessing Message
        """
        # Create new message ID if none is given
        msg_id = uuid.uuid4()
        # get the latency between the two participants
        # Assemble message
        message = Message(self, msg_id, send_id, rec_id, msg,
                          msg_type, gossip, response=response, prev_msg=prev_msg)
        # Send message to receiver
        delivery_process = self.process(self.message_delivery(message))
        # Put message in gloabal history, gets cleared every timestep by the monitor process
        self.messages.append(message)
        # Return messsage to sender to put it into the history
        return message

    def message_delivery(self, message):
        yield self.timeout(message.latency)
        self.get_participant(message.rec_id).msg_pipe.put(message)

    def get_latency(self, send_id, rec_id):
        """
        Parameter send_id as string: ID of sender
        Paramater rec_id as string: ID of recipient
        Returns float: Latency in seconds
        """
        my_random = Random()
        my_random.seed(str(self.now) + str(send_id) + str(rec_id))
        sender = self.get_participant(send_id)
        receiver = self.get_participant(rec_id)

        # Single hop/Device2Device Connection via 5G bands
        if self.config["simulation"]["connection"] == "single-hop":
            distance = self.get_distance(
                sender.phy_x, sender.phy_y, receiver.phy_x, receiver.phy_y)
            high_band_distance = self.config["bands"]["5G-High"]["distance"]
            medium_band_distance = self.config["bands"]["5G-Medium"]["distance"]
            low_band_distance = self.config["bands"]["5G-Low"]["distance"]

            # Deviaton formular: (distance - Distmin)/(Distmax -Distmin) * (MaxDev - MinDev) + MinDev
            # Squashes the distance from the participant between [MinDev, MaxDev] and is multiplies with the standard latency
            # High-Band 5G
            if(distance < high_band_distance):
                high_deviation = (distance - 0) / \
                    (high_band_distance - 0) * (1.25 - 0.75) + 0.75
                return self.config["bands"]["5G-High"]["latency"]/1000 * my_random.randint(90, 110)/100 * high_deviation
            # Medium-Band 5G
            elif (distance < medium_band_distance):
                medium_deviation = (distance - high_band_distance)/(
                    medium_band_distance - high_band_distance) * (1.25 - 0.75) + 0.75
                return self.config["bands"]["5G-Medium"]["latency"]/1000 * my_random.randint(90, 110)/100 * medium_deviation
            # Low-Band 5G
            elif (distance < low_band_distance):
                low_deviation = (distance - medium_band_distance) / \
                    (low_band_distance - medium_band_distance) * \
                    (1.25 - 0.75) + 0.75
                return self.config["bands"]["5G-Low"]["latency"]/1000 * my_random.randint(90, 110)/100 * low_deviation
            # 3G
            else:
                return 0.15

        # Latency calculation for multihop between client and node connection is the following:
        # Latency = Sum ( Transmission delay + Propagation + Processing + Queuing )
        # Transmission/Serialization delay = -0.008 * bandwidth Gbps + 0.088  (Gpbs is usually between 0.1 - 1 for end users)
        # Propagation = distance km * 0.0035 ms/km
        # Processing = [0.010, 0.030]ms + Network error (= constant 0.5ms) -> depending on Hardware
        # Queing = 1 / (1 * bandwidth Gbps) with upper limit of 5ms
        elif self.config["simulation"]["connection"] == "multi-hop":

            # Connection between 2 nodes the less good bandwidth is used
            if isinstance(sender, FogNode) and isinstance(receiver, FogNode):

                bandwidth = min(sender.get_bandwidth(),
                                receiver.get_bandwidth())
                transmission_delay = -0.008 * bandwidth + 0.088
                # basically no distance as we are connected via backhaul
                propagation_delay = 0 * 0.0035
                processing_delay = sender.hardware * 0.01 + 0.05
                queuing_delay = min(5, 1/(2 * bandwidth))
            # Connection between client and node
            else:
                # Checking which participant is Node and who is Client
                client = sender if isinstance(
                    sender, MobileClient) else receiver
                node = sender if isinstance(sender, FogNode) else receiver

                # Calculating the physical distance from each participant to the cell tower
                celltower_id_cl, distance_cl = self.get_nearest_celltower(client)
                celltower_id_n, distance_n = self.get_nearest_celltower(node)
                distance = distance_cl + distance_n
                transmission_delay = -0.008 * node.get_bandwidth() + 0.088
                propagation_delay = distance/1000 * 0.0035
                processing_delay = node.hardware * 0.01 + 0.05
                queuing_delay = min(50, 1/(2 * node.get_bandwidth()))

            return (transmission_delay + propagation_delay + processing_delay + queuing_delay)/1000

    def get_distance(self, send_x, send_y, rec_x, rec_y):
        """Calculates the physical distance between to points in meters

        Args:
            send_x (float): x coordinate of the sending participant
            send_y (float): y coordinate of the sending participant
            rec_x (float): x coordinate of the receiving participant
            rec_y (float): y coordinate of the receiving participant

        Returns:
            float: distance between the two participants in meters
        """
        distance = math.sqrt((rec_x - send_x)**2 + (rec_y - send_y)**2)
        return distance

    def get_message(self, msg_id):
        return next((message for message in self.messages if message.id == msg_id), None)

    def generate_boundaries(self, x_trans, y_trans, method="center"):
        """Calculates the boundaries of the simulation based on the map boundaries and the size of the area

        Args:
            x_trans (int): width of the area (in x direction)
            y_trans (int): lenght of the area (in y direction)
            method (str, optional): Sample method of the area. Either "center" or "random" in respect to the whole map. Defaults to "center".
        """
        # random method
        if(method == "random"):
            x_lower = random.randrange(
                int(self.config["map"]["x_min"]), int(self.config["map"]["x_max"]))
            y_lower = random.randrange(
                int(self.config["map"]["y_min"]), int(self.config["map"]["y_max"]))
        # center method
        elif(method == "center"):
            x_lower = int((self.config["map"]["x_min"] +
                           self.config["map"]["x_max"])/2 - x_trans/2)
            y_lower = int((self.config["map"]["y_min"] +
                           self.config["map"]["y_max"])/2 - y_trans/2)

        else:
            raise RuntimeError(
                "Unknown area selection method. Expected \'random\' or \'center\', found {}".format(method))

        x_upper = x_lower + x_trans
        y_upper = y_lower + y_trans

        return ((x_lower, x_upper, y_lower, y_upper))

    def get_neighbours(self, req_node, n=4):
        """Calculates the nearest physical neighbours for a given node. Is used for the Vivaldi protocol

        Args:
            req_node (FogNode): The node requesting the nearest physical neighbours
            n (int, optional): amount of neighbours. Defaults to 4 as proposed by Dabek et. al.

        Returns:
            [List]: The first n elements of a sorted List of nearby nodes by physical distance
        """
        neighbours = []
        for node in self.nodes:
            # skip the requesting node
            if(node["id"] == req_node.id):
                continue
            a_x, a_y = req_node.get_coordinates()
            b_x, b_y = node["obj"].get_coordinates()
            dist = self.get_distance(a_x, a_y, b_x, b_y)
            neighbours.append({"id": node["id"], "distance": dist})
        # Sort list by distance ascending
        sorted_neighbours = sorted(neighbours, key=itemgetter('distance'))
        return sorted_neighbours[:4]

    def get_closest_node(self, client_id):
        """Gets the closest node to the client based on the latency between client and Node
        Used for the baseline protocol

        Args:
            client_id (UUID): UUID of the client

        Returns:
            UUID: UUID of the node
        """

        latencies = []
        for node in self.nodes:
            if(len(node["obj"].clients) < node["obj"].slots):
                lat = self.get_latency(client_id, node["obj"].id)
                latencies.append(
                    {"id": node["id"], "lat": lat, 'slots': node["obj"].slots, 'clients': len(node["obj"].clients)})

        # Secondary sort by ID, primary sort b latency
        latencies = sorted(latencies, key=itemgetter('id'))
        sorted_lat = sorted(latencies, key=itemgetter('lat'))
        # When there is no node with an open slot we return None
        # This only happens when there are more clients than slots in the whole scenario
        if not sorted_lat:
            return None

        closest_node = sorted_lat.pop(0)
        # print("closest node {} has a current workload of {}".format(closest_node.get("id"), closest_node.get('clients')/closest_node.get('slots')))
        return closest_node.get("id")

    def monitor(self):
        runtime = self.config["simulation"]["runtime"]
        modulus = runtime / 10
        timestamp = 0
        while(True):

            # if(self.now == 0):
            #     print("Runtime: {}/{}".format(self.now, runtime))
            # elif(self.now % modulus == 0):
            #     print("Runtime: {}/{}".format(self.now, runtime))
            duration = round(time.perf_counter() - timestamp, 2)
            timestamp = time.perf_counter()
            print("Runtime: {}/{} in {} seconds with {} messages".format(self.now,
                                                                         runtime, duration, len(self.messages)))
            # print("Runtime: {}/{} in {} seconds with".format(self.now, runtime, duration))
            # clear message history
            self.messages = []
            yield self.timeout(1)

    def get_nearest_celltower(self, client):
        celltowers = []
        for celltower in self.celltowers:
            a_x, a_y = client.get_coordinates()
            b_x, b_y = celltower["obj"].get_coordinates()
            dist = self.get_distance(a_x, a_y, b_x, b_y)
            celltowers.append({"id": celltower.get('id'), "distance": dist})
        # Sort list by distance ascending
        sorted_celltowers = sorted(celltowers, key=itemgetter('distance'))
        nearest_celltower = sorted_celltowers.pop(0)
        return nearest_celltower.get('id'), nearest_celltower.get('distance')
