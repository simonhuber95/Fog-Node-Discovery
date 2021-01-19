from matplotlib import pyplot as plt
from pathlib import Path
import os
import pandas as pd
import numpy as np
import seaborn as sns


def plot_data(columns, titles, y_labels, scenario=None, entity="Client", skip_rows=0, header=0):
    """Plot data from measurements
    Iterates over all columns and collects the values for every NCS for the specific column
    Scenarios define how the date is presented, line graph over client ratio for the standerd scenario, bar plot for the alternative scenarios

    Args:
        columns (List): The Columns of the Pandas Dataframe which shall be plotted
        titles (List): The titles for the graphs for the corresponding columns
        y_labels (List): The labels for the y-axis for the graphs for the corresponding columns
        scenario (str, optional): The scenario to be plotted. Defaults to None.
        entity (str, optional): The entity to be plotted, either Client, Node or Time. Defaults to "Client".
        skip_rows (int, optional): How many rows should be skipped. Defaults to 0.
        header (int, optional): Row index of the header. Defaults to 0.
    """
    x_values = []
    for idx, column in enumerate(columns):
        y_values = []
        for ncs in NCSystems:
            ncs_values = []
            ncs_errors = []
            ncs_upper_q = []
            ncs_lower_q =[]
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    if file.endswith(".csv") and entity.casefold() in file.casefold() and ncs.casefold() in file.casefold() and (not scenario or scenario.casefold() in file.casefold()):
                        if(not scenario and not file.startswith(entity)):
                            continue
                        # For every NCS collect data of column(y) vs the ratio(x)
                        ratio = file.split("_")[-1][:-4]
                        if float(ratio) <= 1:
                            if ratio not in x_values:
                                x_values.append(ratio)
                            df = pd.read_csv(os.path.join(
                                root, file), skiprows=skip_rows, header=header)
                            if entity == "Time":
                                df = df.replace(0, np.NaN)
                            ncs_values.append(df[column].std(axis=0))
                            ncs_errors.append(df[column].std(axis=0))
                            ncs_upper_q.append(df[column].quantile(q=0.75))
                            ncs_lower_q.append(df[column].quantile(q=0.25))

            y_values.append(
                {"ncs": ncs, "values": ncs_values, "errors": ncs_errors, "upper_q": ncs_upper_q, "lower_q": ncs_lower_q})

        if scenario:
            x = np.arange(4)
            ncsy_values = [sub['values'][0] for sub in y_values]
            fig, ax = plt.subplots()
            ax = plt.bar(x, ncsy_values, width=0.5)
            plt.xticks(x, NCSystems)
            plt.ylabel(y_labels[idx])
            plt.title(titles[idx])
        else:
            for ncs in y_values:
                ncsy_values = ncs.get('values')
                ncsy_errors = ncs.get('errors')
                ncsy_upper_q = ncs.get("upper_q")
                ncsy_lower_q = ncs.get("lower_q")
                # Order the values
                ncsx_values, ncsy_values = zip(
                    *sorted(zip(x_values, ncsy_values)))
                _, ncsy_errors = zip(
                    *sorted(zip(x_values, ncsy_errors)))
                _, ncsy_upper_q = zip(
                    *sorted(zip(x_values, ncsy_upper_q)))
                _, ncsy_lower_q = zip(
                    *sorted(zip(x_values, ncsy_lower_q)))
                # print(ncsy_lower_q, ncs_upper_q)
                lower_band = np.array(ncsy_values)-np.array(ncsy_errors) #np.array(ncsy_lower_q) 
                upper_band = np.array(ncsy_values)+np.array(ncsy_errors) #np.array(ncsy_upper_q)
                ax = plt.plot(ncsx_values, ncsy_values, '--')
                # plt.fill_between(ncsx_values, lower_band, upper_band, alpha=0.2, antialiased=True)
            plt.xlabel('Client Ratio')
            plt.ylabel(y_labels[idx])
            plt.legend(NCSystems, loc='upper left')
            plt.title(titles[idx])

        print("Save Figure", str(scenario or '')+entity+'_'+column)

        if scenario:
            folder = fig_path = os.path.join(plt_path, scenario)
            if not os.path.isdir(folder):
                os.mkdir(folder)
            fig_path = os.path.join(
                # plt_path, scenario, scenario+entity+'_'+column)
                plt_path, scenario, scenario+'StdError_'+entity+'_'+column)
        else:
            # fig_path = os.path.join(plt_path, entity+'_'+column)
            fig_path = os.path.join(plt_path, 'Stdrror_'+entity+'_'+column)
        plt.savefig(fig_path)
        plt.cla()
        plt.clf()
        plt.close()


base_path = Path().absolute()
plt_path = os.path.join(base_path, "plots")

NCSystems = ["Baseline", "Vivaldi", "Meridian", "Random"]
client_columns = ["reconnections", "lat_mean", "total_msgs", "lost_msgs",
                  "rtt_rmse", "opt_rate", "discovery_rmse", "discovery_rate"]
client_titles = ["Reconnections per client", "Average latency", "Total messages per client", "Lost messages per client",
                 "RMSE of the RTT", "Optimal connection rate", "RMSE of the selection", "Optimal selection rate"]
client_titles = ["Std Dev reconnections per client", "Std Dev latency", "Std Dev total messages per client", "Std Dev lost messages per client",
                 "Std Dev RMSE of the RTT", "Std Dev Optimal connection rate", "Std Dev RMSE of the selection", "Std Dev optimal selection rate"]


client_y_labels = ["", "Latency in ms", "",
                   "", "RMSE in ms", "", "RMSE in ms", ""]
node_columns = ["avg workload", "avg clients", "avg bandwidth",
                "total_msgs", "out_msgs", "in_msgs", "max workload", "max clients"]
node_titles = ["Average workload", "Avg Clients", "Avg Bandwidth", "Total messages per node",
               "Outgoing messages per node", "Incoming messages per node", "Maximum workload", "Maximum Clients"]
node_titles = ["Std Dev average workload", "Std Dev average Clients", "Std Dev average Bandwidth", "Std Dev total messages per node",
               "Std Dev outgoing messages per node", "Std Dev incoming messages per node", "Std Dev maximum workload", "Std Dev maximum Clients"]
node_y_labels = ["in %", "", "in Gbps", "", "", "", "in %", ""]

time_columns = ["unique discoveries", "opt_choice"]
time_titles = ["Std Dev unique selections", "Std Dev optimal selection"]
time_y_labels = ["", "in %"]

plot_data(client_columns, client_titles, client_y_labels, entity="Client")
plot_data(node_columns, node_titles, node_y_labels, entity="Node")
plot_data(time_columns, time_titles, time_y_labels, entity="Time")

# plot_data(client_columns, client_titles, client_y_labels,scenario="Germany", entity="Client")
# plot_data(node_columns, node_titles, node_y_labels, scenario= "Germany", entity="Node")
# plot_data(time_columns, time_titles, time_y_labels, scenario= "Germany", entity="Time")

# plot_data(client_columns, client_titles, client_y_labels, scenario= "Berlin", entity="Client")
# plot_data(node_columns, node_titles, node_y_labels, scenario= "Berlin", entity="Node")
# plot_data(time_columns, time_titles, time_y_labels, scenario= "Berlin", entity="Time")
