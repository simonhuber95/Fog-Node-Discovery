import time
from .node import FogNode

class Message(object):
    def __init__(self, env, msg_id, send_id, rec_id, body, msg_type, gossip, response = False, prev_msg=None):
        
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
        if (isinstance(self.env.get_participant(self.send_id), FogNode) and isinstance(self.env.get_participant(self.rec_id), FogNode)):
            return None, None
        elif(self.msg_type == 3):
            return None, None
        elif(self.response):
            prev_msg = self.prev_msg
            prev_opt_node = prev_msg.opt_node
            opt_latency = self.env.get_latency(prev_opt_node, self.rec_id)
            return prev_opt_node, opt_latency
        else:
            opt_node = self.env.get_closest_node(self.send_id)
            opt_latency = self.env.get_latency(self.send_id, opt_node)
            return opt_node, opt_latency
        
    def __str__(self):
        return "Message type {} from {} at {}: {}".format(self.msg_type, self.send_id, round(self.timestamp, 2), self.body)
