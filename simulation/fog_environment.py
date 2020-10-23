from simpy import Environment
import math
import uuid
import random


class FogEnvironment(Environment):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.clients = []
        self.nodes = []
        self.boundaries = tuple()

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

    def send_message(self, send_id, rec_id, msg, msg_type=1, msg_id=None):
        """
        Parameter send_id as string: ID of sender
        Paramater rec_id as string: ID of recipient
        Parameter msg as string: Message to be send
        Parameter msg_type as int *optional: type of message -> 1: regular message (default), 2: Closest node request, 3: Node discovery
        Parameter msg_id as uuid *optional: unique id of the message, if none is given a new uuid is created
        Not complete. env.timeout() is not working for some reason, so the delay has to be awaited at recipient
        """
        # Create new message ID if none is given
        if not msg_id:
            msg_id = uuid.uuid4()
        # get the latency between the two participants
        latency = self.get_latency(send_id, rec_id)
        # yield env.timeout(latency)
        # Assemble message
        message = {"msg_id": msg_id, "send_id": send_id, "rec_id": rec_id,
                   "timestamp": self.now, "msg": msg, "msg_type": msg_type, "latency": latency}
        # Send message to receiver
        self.get_participant(rec_id).msg_pipe.put(message)
        # Return messsage to sender to put it into the history
        return message

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
        distance = math.sqrt((rec_x - send_x)**2 + (rec_y - send_y)**2)
        return distance

    def get_boundaries(self, x_trans, y_trans, method="center"):
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
        x_upper = x_lower + x_trans
        y_upper = y_lower + y_trans

        return((x_lower, x_upper, y_lower, y_upper))
