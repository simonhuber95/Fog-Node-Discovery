class ReconnectionRules(object):
    def __init__(self, env):
        self.env = env
        self.all = []

    def latency_rule(self, send_id, rec_id, threshold = 0.7):
        """Latency Rule for client. Checks if the general latency of two participants within the network is lower than a given threshold.

        Args:
            send_id (string): ID of the sender
            rec_id (string): ID of the receiver
            threshold (float): Threshold which represents the upper bound for the general latency. Defaults to 0.7.

        Returns:
            boolean: Whether the latency is lower than the threshold
        """
        latency = self.env.getLatency(send_id, rec_id)
        
        return True if latency < threshold else False
    
    def roundtrip_rule (self, out_history, in_history, threshold = 1):
        """Roundtrip Rule for client. Checks if the roundtrip rule for the last message with corresponding response 
        of two participants within the network is lower than a given threshold.

        Args:
            out_history (list): Outbound message history of client
            in_history (list): Inbound message history of client
            threshold (int, optional): Threshold which represents the upper bound for the roundtrip time. Defaults to 1.

        Returns:
            boolean: Whether the roundtrip time is lower than the threshold
        """
        last_in_msg = in_history[-1]
        last_sender = last_in_msg["send_id"]
        out_msg = list(filter(lambda message: message["send_id"] == last_sender, out_history))[-1]
        roundtrip_time = last_in_msg["timestamp"] - out_msg["timestamp"]
        
        return True if roundtrip_time < threshold else False
    
        
        

