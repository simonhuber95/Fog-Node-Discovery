from simpy import Environment
import math
import uuid
import random
from operator import itemgetter
from .message import Message


class FogEnvironment(Environment):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.clients = []
        self.nodes = []
        self.boundaries = tuple()
        self.messages = []

    def get_participant(self, id):
        """
        Getter for all participants in the network
        Parameter ID as string
        Returns the participant object for the given ID
        """
        return next((elem for elem in [*self.clients, *self.nodes] if elem["id"] == id), None)["obj"]

    def get_random_node(self):
        """
        Returns ID of random fog node
        """
        return random.choice(self.nodes)["id"]

    def send_message(self, send_id, rec_id, msg, gossip, msg_type=1, prev_msg_id=None):
        """
        Parameter send_id as string: ID of sender
        Paramater rec_id as string: ID of recipient
        Parameter msg as string: Message to be send
        Parameter gossip as dict: Gossip of all virtual coordinates
        Parameter msg_type as int *optional: type of message -> 1: regular message (default), 2: Closest node request, 3: Node discovery
        Parameter prev_msg_id as uuid *optional: unique id of the predecessing message
        """
        # Create new message ID if none is given
        msg_id = uuid.uuid4()
        # get the latency between the two participants
        latency = self.get_latency(send_id, rec_id)
        # yield env.timeout(latency)
        # Assemble message
        message = Message(self, msg_id, send_id, rec_id, msg,
                          msg_type, latency, gossip, prev_msg_id=prev_msg_id)
        # message = {"msg_id": msg_id, "send_id": send_id, "rec_id": rec_id,
        #            "timestamp": self.now, "msg": msg, "msg_type": msg_type, "latency": latency, "gossip": gossip}
        # Send message to receiver
        delivery_process = self.process(self.message_delivery(message))
        # self.get_participant(rec_id).msg_pipe.put(message)
        # # Put message in gloabal history
        self.messages.append(message)
        # # Return messsage to sender to put it into the history
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
        sender = self.get_participant(send_id)
        receiver = self.get_participant(rec_id)
        distance = self.get_distance(
            sender.phy_x, sender.phy_y, receiver.phy_x, receiver.phy_y)
        # High-Band 5G
        if(distance < self.config["bands"]["5G-High"]["distance"]):
            return self.config["bands"]["5G-High"]["latency"]/1000 * random.randint(75, 125)/100
        # Medium-Band 5G
        elif (distance < self.config["bands"]["5G-Medium"]["distance"]):
            return self.config["bands"]["5G-Medium"]["latency"]/1000 * random.randint(75, 125)/100
        # Low-Band 5G
        elif (distance < self.config["bands"]["5G-Low"]["distance"]):
            return self.config["bands"]["5G-Low"]["latency"]/1000 * random.randint(75, 125)/100
        # 3G
        else:
            return 1

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
        latencies = []
        for node in self.nodes:
            lat = self.get_latency(client_id, node["obj"].id)
            latencies.append({"id": node["id"], "lat": lat})
        sorted_lat = sorted(latencies, key=itemgetter('lat'))
        closest_node_id = sorted_lat[0]["id"]

        return closest_node_id
