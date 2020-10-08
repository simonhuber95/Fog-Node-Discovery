import pandas as pd
import numpy as np
from functools import reduce


class Metrics(object):
    def __init__(self, env):
        self.env = env

    def all(self):
        rec = self.collect_reconnections()
        lat = self.collect_latency()
        count = self.collect_message_count()
        data_frames = [rec, lat, count]
        df_merged = reduce(lambda left, right: pd.merge(left, right, on=["client_id"],
                                                        how='outer'), data_frames)
        return df_merged

    def collect_reconnections(self):
        reconnections = []
        for client in self.env.clients:
            counter = len(
                list(filter(lambda msg: msg["msg_type"] == 2, client["obj"].out_msg_history)))
            reconnections.append(
                {"client_id": client["obj"].id, "reconnections": counter})
        df = pd.DataFrame(data=reconnections, columns=[
            "client_id", "reconnections"])

        return df

    def collect_latency(self):
        data = []
        for client in self.env.clients:
            latencies = []
            history = [*client["obj"].in_msg_history,
                       *client["obj"].out_msg_history]
            for message in history:
                latencies.append(message["latency"])

            data.append({"client_id": client["obj"].id, "lat_mean": np.mean(
                latencies), "lat_max": np.max(latencies), "lat_min": np.min(latencies)})
        df = pd.DataFrame(data=data, columns=[
                          "client_id", "lat_mean", "lat_max", "lat_min"])
        return df

    def collect_message_count(self):
        data = []
        for client in self.env.clients:
            history = [*client["obj"].in_msg_history,
                       *client["obj"].out_msg_history]

            data.append({"client_id": client["obj"].id, "total_msgs": len(history),  "out_msgs": len(client["obj"].out_msg_history), "in_msgs": len(
                client["obj"].in_msg_history)})
        df = pd.DataFrame(data=data, columns=[
                          "client_id", "total_msgs", "in_msgs", "out_msgs"])
        return df
