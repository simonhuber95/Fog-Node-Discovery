from matplotlib import pyplot as plt
from pathlib import Path
import os
import pandas as pd
import numpy as np


def plot_data(columns, titles, y_labels, scenario=None, entity="Client", skip_rows=0, header=0):
    x_values = []
    for idx, column in enumerate(columns):
        y_values = []
        for ncs in NCSystems:
            ncs_values = []
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    if file.endswith(".csv") and entity.casefold() in file.casefold() and ncs.casefold() in file.casefold() and (not scenario or scenario.casefold() in file.casefold()):
                        # For every NCS collect data of column(y) vs the ratio(x)
                        ratio = file.split("_")[-1][:-4]
                        if float(ratio) <= 1:
                            if ratio not in x_values:
                                x_values.append(ratio)
                            df = pd.read_csv(os.path.join(
                                root, file), skiprows=skip_rows, header=header)
                            if entity == "Time":
                                df = df.replace(0, np.NaN)
                            ncs_values.append(df[column].mean(axis=0))

            y_values.append({"ncs": ncs, "values": ncs_values})

        if scenario:
            x = np.arange(4)
            ncsy_values = [sub['values'][0] for sub in y_values]
            fig, ax = plt.subplots()
            ax = plt.bar(x, ncsy_values, width = 0.5)
            plt.xticks(x, NCSystems)
            plt.ylabel(y_labels[idx])
            plt.title(titles[idx])
        else:
            for ncs in y_values:
                ncsy_values = ncs.get('values')
                ncsx_values, ncsy_values = zip(
                    *sorted(zip(x_values, ncsy_values)))
                ax = plt.plot(ncsx_values, ncsy_values, '--')
            plt.xlabel('Client Ratio')
            plt.ylabel(y_labels[idx])
            plt.legend(NCSystems)
            plt.title(titles[idx])

        print("Save Figure", scenario+'_'+entity+'_'+column)
        
        if scenario:
            folder = fig_path = os.path.join(plt_path, scenario)
            if not os.path.isdir(folder):
                os.mkdir(folder)
            fig_path = os.path.join(
                plt_path, scenario, scenario+'_'+entity+'_'+column)
        else:
            fig_path = os.path.join(plt_path, '_'+entity+'_'+column)
        plt.savefig(fig_path)
        plt.cla()
        plt.clf()
        plt.close()


base_path = Path().absolute()
plt_path = os.path.join(base_path, "plots")
# open the config.yaml as object
NCSystems = ["Baseline", "Vivaldi", "Meridian", "Random"]
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

time_columns = ["unique discoveries", "opt_choice"]
time_titles = ["Unique Discoveries", "Optimal Discovery"]
time_y_labels = ["", "in %"]

# plot_data(client_columns, client_titles, client_y_labels, entity="Client")
# plot_data(node_columns, node_titles, node_y_labels, entity="Node")
# plot_data(time_columns, time_titles, time_y_labels, entity="Time")

plot_data(client_columns, client_titles, client_y_labels,scenario="Germany", entity="Client")
plot_data(node_columns, node_titles, node_y_labels, scenario= "Germany", entity="Node")
plot_data(time_columns, time_titles, time_y_labels, scenario= "Germany", entity="Time")

# plot_data(client_columns, client_titles, client_y_labels, scenario= "Berlin", entity="Client")
# plot_data(node_columns, node_titles, node_y_labels, scenario= "Berlin", entity="Node")
# plot_data(time_columns, time_titles, time_y_labels, scenario= "Berlin", entity="Time")
