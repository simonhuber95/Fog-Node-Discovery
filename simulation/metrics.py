import pandas as pd
import numpy as np
from functools import reduce


class Metrics(object):
    def __init__(self, env):
        self.env = env

    def all_client(self):
        """Collects all client metrics and returns them in a single dataframe

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

    def all_time(self):
        """Collects all metrics over time and returns them in a single dataframe

        Returns:
            DataFrame: Collection of all metrics
        """
        unique = self.collect_unique_discovery()
        choice = self.collect_opt_choice_over_time()
        messages = self.collect_total_messages_over_time()
        data_frames = [messages, unique, choice]
        df_merged = reduce(lambda left, right: pd.merge(left, right, on=["timestamp"],
                                                        how='outer'), data_frames)
        return df_merged.sort_values(by=['timestamp']).fillna(0)

    def all_node(self):
        """Collects all Node metrics and returns them in a single dataframe

        Returns:
            DataFrame: Collection of all metrics
        """
        workload = self.collect_workload()
        messages = self.collect_node_messages()
        data_frames = [workload, messages]
        df_merged = reduce(lambda left, right: pd.merge(left, right, on=["node_id"],
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
                if message.msg_type != 3:
                    latencies.append(message.latency)

            data.append({"client_id": client["obj"].id, "lat_mean": round(np.mean(
                latencies)*1000, 3), "lat_max": round(np.max(latencies)*1000, ), "lat_min": round(np.min(latencies)*1000, 3)})
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
        """Counts the total lost messages for each client

        Returns:
            DataFrame: DataFrame filled with the message counts
        """
        data = []
        for client in self.env.clients:
            filtered_in_history = list(
                filter(lambda message: message.msg_type != 3, client["obj"].in_msg_history))
            filtered_out_history = list(
                filter(lambda message: message.msg_type != 3, client["obj"].out_msg_history))
            in_ids = list(
                map(lambda msg: msg.prev_msg.id, filtered_in_history))
            match_ids = list(
                filter(lambda msg: msg.id not in in_ids, filtered_out_history))
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
            active_time = round(last_msg.timestamp - first_msg.timestamp)
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
                if(in_msg.prev_msg and in_msg.msg_type == 1 and in_msg.opt_latency):
                    # Retrieve request for the incoming response
                    out_msg = next(
                        (message for message in client["obj"].out_msg_history if message.id == in_msg.prev_msg.id), None)
                    y_true.append((out_msg.latency + in_msg.latency) * 1000)
                    y_opt.append(
                        (out_msg.opt_latency + in_msg.opt_latency)*1000)
                    # Counter of optimal node choice
                    opt_choice = opt_choice + 1 if in_msg.opt_node == in_msg.send_id else opt_choice

            opt_rate = opt_choice/len(y_true) if len(y_true) > 0 else 0
            mse = round(
                np.sqrt(np.square(np.subtract(y_true, y_opt)).mean()), 3)
            data.append(
                {"client_id": client["obj"].id, "rtt_rmse": mse, "opt_rate": round(opt_rate, 2)})
        return pd.DataFrame(data=data, columns=["client_id", "rtt_rmse", "opt_rate"])

    def collect_discovery_error(self):
        """Computes the mean-square-error for every message from type 2 of the optimal latency and the latency to the suggested node
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
            for in_msg in (x for x in client["obj"].in_msg_history if x.msg_type == 2 and x.response):
                if in_msg.opt_latency and in_msg.discovered_latency:
                    y_true.append(in_msg.discovered_latency*1000)
                    y_opt.append(in_msg.opt_latency*1000)
                    # Counter of optimal node choice
                    opt_choice = opt_choice + 1 if in_msg.opt_node == in_msg.body else opt_choice

            opt_rate = opt_choice/len(y_true) if len(y_true) > 0 else 0
            rmse = round(
                np.sqrt(np.square(np.subtract(y_true, y_opt)).mean()), 3)
            data.append(
                {"client_id": client["obj"].id, "discovery_rmse": rmse, "discovery_rate": round(opt_rate, 2)})
        return pd.DataFrame(data=data, columns=["client_id", "discovery_rmse", "discovery_rate"])

    def collect_workload_deviation(self):
        """Computes the mean-square-error for every message from type 2 of the optimal latency and the latency to the suggested node
        Computes the percentage how often the client is suggested the perfect node

        Returns:
            DataFrame: DataFrame filled with the latency-mse and perfect suggestion rate per client
        """
        data = []
        for node in self.env.nodes:
            for entry in node.get("obj").workload:
                data.append(
                    {"timestamp": entry.get('timestamp'), "workload": entry.get('workload')})

        df = pd.DataFrame(data=data, columns=["timestamp", "workload"])
        df = df.groupby("timestamp").agg(['std', 'mean', 'min', 'max', ])
        return df

    def collect_unique_discovery(self):
        """Computes the unique discoveries per timestep
        
        Returns:
            DataFrame: DataFrame filled with the Unique discoveries per timestep
        """
        data = []
        for node in self.env.nodes:
            for message in filter(lambda msg: msg.msg_type == 2, node.get('obj').out_msg_history):
                data.append({"timestamp": np.ceil(
                    message.timestamp), "discovery": message.body})
        # Define internal function that creates a set out of the messages of a timestep to count uniques
        def func(messages): return len(set(messages))
        df = pd.DataFrame(data=data, columns=["timestamp", "discovery"])
        df = df.groupby(["timestamp"])['discovery'].agg(
            [('unique discoveries', func)])
        df.reset_index()
        return df

    def collect_total_messages_over_time(self):
        """Computes the total messages per timestep
        
        Returns:
            DataFrame: DataFrame filled with the total messages per timestep
        """
        data = []

        for elem in [*self.env.nodes, *self.env.clients]:
            for message in elem.get('obj').out_msg_history:
                data.append({"timestamp": np.ceil(message.timestamp)})

        df = pd.DataFrame(data=data, columns=["timestamp"])
        df = df.groupby(["timestamp"]).size(
        ).reset_index(name='total messages')
        df.reset_index()
        return df

    def collect_error_over_time(self):
        """Computes the mean-square-error for every message from type 2 of the optimal latency and the latency to the suggestes node
        Computes the percentage how often the client is suggested the perfect node

        Returns:
            DataFrame: DataFrame filled with the latency-mse and perfect suggestion rate per client
        """
        data = []
        for client in self.env.clients:

            # counter for chosing the optimal node
            opt_choice = []
            for in_msg in (x for x in client["obj"].in_msg_history if x.msg_type == 2):
                if in_msg.opt_latency and in_msg.discovered_latency:
                    y_true = in_msg.discovered_latency * 1000
                    y_opt = in_msg.opt_latency * 1000
                    # Counter of optimal node choice
                    opt_choice.append(1 if in_msg.opt_node ==
                                      in_msg.body else 0)
                    timestamp = round(in_msg.timestamp)
                    data.append(
                        {"timestamp": np.ceil(timestamp), "y_true": y_true, "y_opt": y_opt, "discovery_rate": sum(opt_choice)/len(opt_choice)})
        df = pd.DataFrame(data=data, columns=[
                          "timestamp", "y_true", "y_opt", "discovery_rate"])

        df = df.groupby("timestamp").apply(
            lambda x: np.sqrt(np.square(np.subtract(x.y_true, x.y_opt)).mean()))
        return df

    def collect_opt_choice_over_time(self):
        """Computes the mean-square-error for every message from type 2 of the optimal latency and the latency to the suggestes node
        Computes the percentage how often the client is suggested the perfect node

        Returns:
            DataFrame: DataFrame filled with the latency-mse and perfect suggestion rate per client
        """
        data = []
        for client in self.env.clients:
            # counter for chosing the optimal node
            opt_choice = []
            for in_msg in (x for x in client["obj"].in_msg_history if x.msg_type == 2):
                # Counter of optimal node choice
                opt_choice.append(1 if in_msg.opt_node == in_msg.body else 0)
                timestamp = round(in_msg.timestamp)
                data.append(
                    {"timestamp": np.ceil(timestamp),  "opt_choice": sum(opt_choice)/len(opt_choice)})
        df = pd.DataFrame(data=data, columns=["timestamp", "opt_choice"])
        df = df.groupby("timestamp").agg("mean")
        return df

    def collect_workload(self):
        """Computes the min, mean and max workload and bandwidth per Node
        
        Returns:
            DataFrame: DataFrame filled with the min, mean and max workload and bandwidth per node
        """
        data = []
        for node in self.env.nodes:
            workloads = [elem.get(
                'workload') for elem in node["obj"].workload if elem.get('timestamp') > 10]
            clients = [elem.get('clients') for elem in node["obj"].workload if elem.get(
                'timestamp') > 10]
            avg_workload = round(np.mean(workloads), 2)
            max_workload = round(np.max(workloads), 2)
            min_workload = round(np.min(workloads), 2)
            avg_clients = round(np.mean(clients))
            min_clients = round(np.min(clients))
            max_clients = round(np.max(clients))
            min_bandwidth = min(
                1, max(0.1, 1 - (1/(node["obj"].slots)) * (max_clients - 1)))
            avg_bandwidth = min(
                1, max(0.1, 1 - (1/(node["obj"].slots)) * (avg_clients - 1)))
            max_bandwidth = min(
                1, max(0.1, 1 - (1/(node["obj"].slots)) * (min_clients - 1)))
            data.append(
                {"node_id": node["obj"].id, "avg workload": avg_workload, "min workload": min_workload, "max workload": max_workload,
                 "avg clients": avg_clients, "min clients": min_clients, "max clients": max_clients,
                 'avg bandwidth': avg_bandwidth, 'min bandwidth': min_bandwidth, 'max bandwidth': max_bandwidth})
        return pd.DataFrame(data=data, columns=["node_id", "avg workload", "min workload", "max workload",
                                                "avg clients", "min clients", "max clients",
                                                "avg bandwidth", "min bandwidth", "max bandwidth"])

    def collect_node_messages(self):
        """Computes the total, outgoing and incoming message load per Node
        
        Returns:
            DataFrame: DataFrame filled with the total message load per node
        """
        
        data = []
        for node in self.env.nodes:
            history = [*node["obj"].in_msg_history,
                       *node["obj"].out_msg_history]

            data.append({"node_id": node["obj"].id, "total_msgs": len(history),  "out_msgs": len(node["obj"].out_msg_history),
                         "in_msgs": len(node["obj"].in_msg_history)})
        df = pd.DataFrame(data=data, columns=[
                          "node_id", "total_msgs", "out_msgs", "in_msgs"])
        return df
