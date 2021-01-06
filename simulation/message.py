import time
from .node import FogNode

class Message(object):
    def __init__(self, env, msg_id, send_id, rec_id, body, msg_type, gossip, response = False, prev_msg=None):
        """AI is creating summary for __init__

        Args:
            env (FogEnvironment): Fog Environment of the simulation
            msg_id (uuid): Message ID
            send_id (uuid): ID of the sender
            rec_id (uuid): ID of the recipient
            body (any): Message body
            msg_type (int): Message type, either 1, 2, 3 or 4
            gossip (dict): Dictionary of news
            response (bool, optional): Whether the message is a response. Defaults to False.
            prev_msg (Message, optional): The previous message this responds to or None. Defaults to None.
        """
        self.env = env
        self.id = msg_id
        self.send_id = send_id
        self.rec_id = rec_id
        self.timestamp = env.now
        self.body = body
        self.msg_type = msg_type
        self.latency = self.env.get_latency(send_id, rec_id)
        self.gossip = gossip
        self.response = response
        self.prev_msg = prev_msg
        self.opt_node, self.opt_latency = self.calc_optimals()
        if(msg_type == 2 and response):
            self.discovered_latency = self.env.get_latency(body, self.rec_id)
        

    def calc_optimals(self):
        """Calculates the theoretically optimal connection of this message
        This calculation is not used in the simulation directly but by the metric collector to identify the message errors
        Optimals are not calculated for messages from type 3 or messages between nodes

        Returns:
            uuid: ID of the optimal node or None
            float: Latency to the optimal node or None
        """
        if (isinstance(self.env.get_participant(self.send_id), FogNode) and isinstance(self.env.get_participant(self.rec_id), FogNode)):
            return None, None
        elif(self.msg_type == 3):
            return None, None
        elif(self.response):
            prev_msg = self.prev_msg
            prev_opt_node = prev_msg.opt_node
            if prev_opt_node:
                opt_latency = self.env.get_latency(prev_opt_node, self.rec_id)
                return prev_opt_node, opt_latency
            # There is no optimal node because all slots are taken
            else:
                return None, None
        else:
            opt_node = self.env.get_closest_node(self.send_id)
            if opt_node:
                opt_latency = self.env.get_latency(self.send_id, opt_node)
                return opt_node, opt_latency
            # There is no optimal node because all slots are taken
            else:
                return None, None
        
    def __str__(self):
        """String representation of a Message

        Returns:
            str: String representation of a Message
        """
        return "Message type {} from {} at {}: {}".format(self.msg_type, self.send_id, round(self.timestamp, 2), self.body)
