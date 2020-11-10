class Message(object):
    def __init__(self, env, msg_id, send_id, rec_id, body, msg_type, latency, gossip, prev_msg_id=None):
        self.env = env
        self.id = msg_id
        self.send_id = send_id
        self.rec_id = rec_id
        self.timestamp = env.now
        self.body = body
        self.msg_type = msg_type
        self.latency = self.env.get_latency(send_id, rec_id)
        self.gossip = gossip
        self.prev_msg_id = prev_msg_id
        self.opt_node, self.opt_latency = self.calc_optimals()

    def calc_optimals(self):
        if(self.prev_msg_id):
           prev_msg = self.env.get_message(self.prev_msg_id)
           prev_opt_node = prev_msg.opt_node
           opt_latency = self.env.get_latency(prev_opt_node, self.rec_id)
           return prev_opt_node, opt_latency
        else:
            opt_node = self.env.get_closest_node(self.send_id)
            opt_latency = self.env.get_latency(self.send_id, opt_node)
            return opt_node, opt_latency
        
    def __str__(self):
        return "Message {} type {} from {} to {} at {}: {}".format(self.id, self.msg_type, self.send_id, self.rec_id, self.timestamp, self.body)
