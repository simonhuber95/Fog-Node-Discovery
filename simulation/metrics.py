class Metrics(object):
    def __init__(self, env):
        self.env = env
        
    def collect_reconnections(self):
        reconnections = []
        for client in self.env.clients:
            counter = 0
            rec_id = None
            for message in client["obj"].out_msg_history:
                if message["rec_id"] != rec_id:
                    counter += 1
                    rec_id = message["rec_id"]
            reconnections.append({"client_id": client["obj"].id, "reconnections": counter})
        
        return reconnections