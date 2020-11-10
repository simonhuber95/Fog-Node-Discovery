import pandas as pd
import numpy as np
from functools import reduce


class Metrics(object):
    def __init__(self, env):
        self.env = env

    def all(self):
        """Collects all metrics and returns them in a single dataframe

        Returns:
            DataFrame: Collection of all metrics
        """
        rec = self.collect_reconnections()
        lat = self.collect_latency()
        count = self.collect_message_count()
        lost = self.collect_lost_messages()
        active = self.collect_active_time()
        opt_mse = self.collect_optimal_error()
        disc_mse = self.collect_discovery_error()
        data_frames = [rec, lat, count, lost, active, opt_mse, disc_mse]
        df_merged = reduce(lambda left, right: pd.merge(left, right, on=["client_id"],
                                                        how='outer'), data_frames)
        return df_merged

    def collect_reconnections(self):
        """Counts how often a client requests a new connection (msg_type 2)

        Returns:
            DataFrame: DataFrame filled with the reconnections per client
        """
        reconnections = []
        for client in self.env.clients:
            counter = len(
                list(filter(lambda msg: msg.msg_type == 2, client["obj"].out_msg_history)))
            reconnections.append(
                {"client_id": client["obj"].id, "reconnections": counter})
        df = pd.DataFrame(data=reconnections, columns=[
            "client_id", "reconnections"])

        return df

    def collect_latency(self):
        """Collects the average, min and max latency for each client

        Returns:
            DataFrame: DataFrame filled with the latencies
        """
        data = []
        for client in self.env.clients:
            latencies = []
            history = [*client["obj"].in_msg_history,
                       *client["obj"].out_msg_history]
            for message in history:
                latencies.append(message.latency)

            data.append({"client_id": client["obj"].id, "lat_mean": np.mean(
                latencies), "lat_max": np.max(latencies), "lat_min": np.min(latencies)})
        df = pd.DataFrame(data=data, columns=[
                          "client_id", "lat_mean", "lat_max", "lat_min"])
        return df

    def collect_message_count(self):
        """Counts the total, incoming and outgoing messages for each client

        Returns:
            DataFrame: DataFrame filled with the message counts
        """
        data = []
        for client in self.env.clients:
            history = [*client["obj"].in_msg_history,
                       *client["obj"].out_msg_history]

            data.append({"client_id": client["obj"].id, "total_msgs": len(history),  "out_msgs": len(client["obj"].out_msg_history),
                         "in_msgs": len(client["obj"].in_msg_history)})
        df = pd.DataFrame(data=data, columns=[
                          "client_id", "total_msgs", "out_msgs", "in_msgs"])
        return df

    def collect_lost_messages(self):
        data = []
        for client in self.env.clients:
            in_ids = list(
                map(lambda msg: msg.prev_msg_id, client["obj"].in_msg_history))
            match_ids = list(
                filter(lambda msg: msg.id not in in_ids, client["obj"].out_msg_history))
            data.append(
                {"client_id": client["obj"].id, "lost_msgs": len(match_ids)})
        return pd.DataFrame(data=data, columns=[
            "client_id", "lost_msgs"])

    def collect_active_time(self):
        """Counts how long the client was active in the simulation

        Returns:
            DataFrame: DataFrame filled with the active time per client
        """
        data = []
        for client in self.env.clients:
            first_msg = client["obj"].out_msg_history[0]
            last_msg = client["obj"].out_msg_history[-1]
            active_time = last_msg.timestamp - first_msg.timestamp
            data.append(
                {"client_id": client["obj"].id, "active_time": active_time})
        return pd.DataFrame(data=data, columns=["client_id", "active_time"])

    def collect_optimal_error(self):
        """Computes the mean-square-error for every message from type 1 of the optimal latency and the actual latency
        Computes the percentage how often the client connects to the perfect node 

        Returns:
            DataFrame: DataFrame filled with the roundtrip-time-mse and perfect connerction rate per client
        """
        data = []
        for client in self.env.clients:
            # Actual rtt
            y_true = []
            # Optimal rtt
            y_opt = []
            # counter for chosing the optimal node
            opt_choice = 0
            for in_msg in client["obj"].in_msg_history:
                if(in_msg.prev_msg_id and in_msg.msg_type == 1):
                    # Retrieve request for the incoming response
                    out_msg = next(
                        (message for message in client["obj"].out_msg_history if message.id == in_msg.prev_msg_id), None)
                    y_true.append(out_msg.latency + in_msg.latency)
                    y_opt.append(out_msg.opt_latency + in_msg.opt_latency)
                    # Counter of optimal node choice
                    opt_choice = opt_choice + 1 if in_msg.opt_node == in_msg.send_id else opt_choice  
                    
            opt_rate = opt_choice/len(y_true) if len(y_true)>0 else 0
            mse = np.square(np.subtract(y_true, y_opt)).mean()
            data.append(
                {"client_id": client["obj"].id, "rtt_mse": mse, "opt_rate": round(opt_rate, 2)})
        return pd.DataFrame(data=data, columns=["client_id", "rtt_mse", "opt_rate"])
    
    def collect_discovery_error(self):
        """Computes the mean-square-error for every message from type 2 of the optimal latency and the latency to the suggestes node
        Computes the percentage how often the client is suggested the perfect node

        Returns:
            DataFrame: DataFrame filled with the latency-mse and perfect suggestion rate per client
        """
        data = []
        for client in self.env.clients:
            # Actual latency to discovered node
            y_true = []
            # Latency to optimal node
            y_opt = []
            # counter for chosing the optimal node
            opt_choice = 0
            for in_msg in (x for x in client["obj"].in_msg_history if x.msg_type == 2):
                # TODO stimmt noch nicht, eigentlich müsste die opt_latency mit der latency der discoverd node verglichen werden
                y_true.append(in_msg.latency)
                y_opt.append(in_msg.opt_latency)
                # Counter of optimal node choice
                opt_choice = opt_choice + 1 if in_msg.opt_node == in_msg.body else opt_choice 
                 
            opt_rate = opt_choice/len(y_true) if len(y_true)>0 else 0
            mse = np.square(np.subtract(y_true, y_opt)).mean()
            data.append(
                {"client_id": client["obj"].id, "discovery_mse": mse, "discovery_rate": round(opt_rate, 2)})
        return pd.DataFrame(data=data, columns=["client_id", "discovery_mse", "discovery_rate"])
        