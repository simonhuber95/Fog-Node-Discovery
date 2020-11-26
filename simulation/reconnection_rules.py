class ReconnectionRules(object):
    def __init__(self, env):
        self.env = env
        self.all = []

    def latency_rule(self, send_id, rec_id, threshold=0.7):
        """Latency Rule for client. Checks if the general latency of two participants within the network is lower than a given threshold.

        Args:
            send_id (string): ID of the sender
            rec_id (string): ID of the receiver
            threshold (float): Threshold which represents the upper bound for the general latency. Defaults to 0.7.

        Returns:
            boolean: Whether the latency is lower than the threshold
        """
        latency = self.env.get_latency(send_id, rec_id)
        check = True if latency < threshold else False
        # if not check: print("latency rule failed")
        return check

    def roundtrip_rule(self, out_history, in_history, threshold=1):
        """Roundtrip Rule for client. Checks if the roundtrip rule for the last message with corresponding response 
        of two participants within the network is lower than a given threshold.

        Args:
            out_history (list): Outbound message history of client
            in_history (list): Inbound message history of client
            threshold (int, optional): Threshold which represents the upper bound for the roundtrip time. Defaults to 1.

        Returns:
            boolean: Whether the roundtrip time is lower than the threshold
        """
        last_in_msg = next(
            (message for message in reversed(in_history) if message.msg_type == 1), None)
        # No task has been sent yet
        if(not last_in_msg):
            return True
        out_msg = next(
            (message for message in out_history if message.id == last_in_msg.prev_msg.id), None)
        # Message has not come back so RTT cannot be calculated
        if(not out_msg):
            return True

        roundtrip_time = last_in_msg.rec_timestamp - out_msg.timestamp
        check = True if roundtrip_time < threshold else False
        # if not check: print("Roundtrip rule failed")
        return check 

    def timeout_rule(self, out_history, in_history, threshold=1.5):
        """Timeout Rule for Client. Checks if the time past for a non received answer exceeds the threshold

        Args:
            out_history (list): Outbound message history of client
            in_history (list): Inbound message history of client
            threshold (int, optional): Threshold which represents the upper bound for the roundtrip time. Defaults to 1.
        """
        last_in_msg = in_history[-1]
        out_msg = next(
            (message for message in out_history if last_in_msg.prev_msg and message.id == last_in_msg.prev_msg.id), None)
        # Message was no respone, so we dont care
        if(not out_msg):
            return True
        # If Out Message has been sent longer than threshold and no answer is received
        if(self.env.now - out_msg.timestamp > threshold and not last_in_msg):
            return False
        else:
            return True
