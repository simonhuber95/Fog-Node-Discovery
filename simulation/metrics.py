import pandas as pd
import numpy as np


class Metrics(object):
    def __init__(self, env):
        self.env = env

    def all(self):
        rec = self.collect_reconnections()
        lat = self.collect_latency()
        return pd.merge(rec, lat, on="client_id")

    def collect_reconnections(self):
        reconnections = []
        for client in self.env.clients:
            counter = 0
            rec_id = None
            for message in client["obj"].out_msg_history:
                if message["rec_id"] != rec_id:
                    counter += 1
                    rec_id = message["rec_id"]
            reconnections.append(
                {"client_id": client["obj"].id, "reconnections": counter})
        df = pd.DataFrame(data=reconnections, columns=[
            "client_id", "reconnections"])

        return df

    def collect_latency(self):
        data = []
        for client in self.env.clients:
            latencies = []

            full_history = client["obj"].in_msg_history.ex
            print(full_history)
            for message in full_history:
                latencies.append(message["latency"])

            data.append({"client_id": client["obj"].id, "lat_mean": np.mean(
                latencies), "lat_max": np.max(latencies), "lat_min": np.min(latencies)})
        df = pd.DataFrame(data=data, columns=[
                          "client_id", "lat_mean", "lat_max", "lat_min"])
        return df
