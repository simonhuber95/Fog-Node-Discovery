from matplotlib import pyplot as plt
from pathlib import Path
import os
import pandas as pd


def plot_data(columns, titles, y_labels, entity="Client", skip_rows=0, header=0):
    x_values = []
    for idx, column in enumerate(columns):
        y_values = []
        for ncs in NCSystems:
            ncs_values = []
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    if file.endswith(".csv") and entity in file and ncs in file:
                        # For every NCS collect data of column(y) vs the ratio(x)
                        ratio = file.split("_")[-1][:-4]
                        if float(ratio) <= 1:
                            if ratio not in x_values:
                                x_values.append(ratio)
                            df = pd.read_csv(os.path.join(
                                root, file), skiprows=skip_rows, header=header)
                            ncs_values.append(df[column].mean(axis=0))
                            
            y_values.append({"ncs": ncs, "values": ncs_values})

        for ncs in y_values:
            ncsy_values = ncs.get('values')
            ncsx_values, ncsy_values = zip(*sorted(zip(x_values, ncsy_values)))
            ax = plt.plot(ncsx_values, ncsy_values, '--')
            
        print("Save Figure", entity+'_'+column)
        plt.xlabel('Client Ratio')
        plt.ylabel(y_labels[idx])
        plt.legend(NCSystems)
        plt.title(titles[idx])
        fig_path = os.path.join(plt_path, entity+'_'+column)
        plt.savefig(fig_path)
        plt.cla()
        plt.clf()


base_path = Path().absolute()
plt_path = os.path.join(base_path, "plots")
# open the config.yaml as object
NCSystems = ["baseline", "vivaldi", "meridian", "random"]
client_columns = ["reconnections", "lat_mean", "total_msgs", "lost_msgs",
                  "rtt_rmse", "opt_rate", "discovery_rmse", "discovery_rate"]
client_titles = ["reconnections", "Average latency", "Total messages per client", "Lost messages per client",
                 "RMSE of the rtt", "Optimal connection rate", "RMSE of the discovery", "Optimal discovery rate"]
client_y_labels = ["", "Latency in ms", "",
                   "", "RMSE in ms", "", "RMSE in ms", ""]
node_columns = ["avg workload", "avg clients", "avg bandwidth",
                "total_msgs", "out_msgs", "in_msgs", "max workload", "max clients"]
node_titles = ["Average workload", "Avg Clients", "Avg Bandwidth", "Messages per node",
               "Out messages per node", "In messages per node", "Maximum workload", "Maximum Clients"]
node_y_labels = ["in %", "", "in Gbps", "", "", "", "in %", ""]

plot_data(client_columns, client_titles, client_y_labels, entity="Client")
plot_data(node_columns, node_titles, node_y_labels, entity="Node")
