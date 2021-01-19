import simpy
from simulation.client import MobileClient
from simulation.node import FogNode
from simulation.celltower import Celltower
from simulation.metrics import Metrics
from simulation.fog_environment import FogEnvironment
import xml.etree.ElementTree as et
import uuid
import geopandas as gpd
import yaml
from pathlib import Path
from random import Random
import math
from simulation.visualize import *
import warnings


def main():
    # Creating a Random instance with a seed
    my_random = Random("Fog-Node-Discovery")
    # Set base path of the project
    base_path = Path().absolute()

    # open the config.yaml as object
    with open(base_path.joinpath("config.yml"), "r") as ymlfile:
        config = yaml.load(ymlfile, Loader=yaml.FullLoader)

    # set path to the OpenBerlinScenario.xml
    client_path = base_path.joinpath(config["clients"]["path"])
    # set path to the Cell Tower json
    nodes_path = base_path.joinpath(config["nodes"]["path"])
    # Set amount of client
    max_clients = config["clients"]["max_clients"]
    # Set the client ratio
    client_ratio = config["clients"]["client_ratio"]
    # Set amount of nodes
    min_nodes = config["nodes"]["min_nodes"]
    max_nodes = config["nodes"]["max_nodes"]
    # Set the bandwidth
    unlimited_bandwidth = config["nodes"]["unlimited_bandwidth"]
    # Set scenario
    scenario = config["simulation"]["scenario"]
    # Create map of biggest cities in Germany in GK4 coordinates
    cities = {"Hamburg": (4367563.06, 5937041.67), "München": (4468503.333, 5333317.780),
              "Köln": (4146019.92, 5656896.35), "Frankfurt": (4259564.48, 5559334.88), "Stuttgart": (4292986.66, 5408460.24),
              "Düsseldorf": (4135787.36, 5690093.14), "Leipzig": (4527247.69, 5689904.87), "Dortmund": (4185687.75, 5717881.24),
              "Dresden": (4624335.26, 5661644.35), "Bremen": (4282562.56, 5913172.68)}

    # Init Environment
    print("Preparing Environment")
    env = FogEnvironment(config)
    # Reading Client movement patterns
    client_data = et.parse(client_path)
    # Reading Node coordinates from json
    nodes_gdf = gpd.read_file(nodes_path)

# ------------------------------------------------------
# ------------------ Area Selection --------------------
# ------------------------------------------------------
    # Selecting an are for the simulation
    # If "all" the whole defined area is selected
    # Else the area within the boundaries is selected. The Selected are must have enough Cell Towers/Fog Nodes to be valid
    if config["simulation"]["area_selection"] == "all":
        (x_lower, x_upper, y_lower, y_upper) = (
            config["map"]["x_min"], config["map"]["x_max"], config["map"]["y_min"], config["map"]["y_max"])
        env.boundaries = (x_lower, x_upper, y_lower, y_upper)
        filtered_nodes_gdf = nodes_gdf.cx[x_lower:x_upper, y_lower:y_upper]

    else:
        while True:
            # Get boundaries of simulation
            (x_lower, x_upper, y_lower, y_upper) = env.generate_boundaries(
                config["simulation"]["area"], config["simulation"]["area"], method=config["simulation"]["area_selection"])
            # Filter Nodes within boundary
            filtered_nodes_gdf = nodes_gdf.cx[x_lower:x_upper, y_lower:y_upper]
            # Check if area is valid
            if(not min_nodes or len(filtered_nodes_gdf) >= min_nodes):
                env.boundaries = (x_lower, x_upper, y_lower, y_upper)
                break

    print("Simulation area x: {} - {}, y: {} - {}".format(x_lower,
                                                          x_upper, y_lower, y_upper))

# ------------------------------------------------------
# ------------------ Cell Towers & Fog Nodes -----------
# ------------------------------------------------------
    # Slot counter to calculate the client ratio later on
    total_slots = 0
    for index, node_entry in filtered_nodes_gdf.iterrows():

        node_id = uuid.uuid4()
        cell_id = uuid.uuid4()
        # Place Cell Towers
        celltower = Celltower(env, id=cell_id,
                              phy_x=node_entry["geometry"].x,
                              phy_y=node_entry["geometry"].y,
                              verbose=config["simulation"]["verbose"])
        env.celltowers.append({"id": cell_id, "obj": celltower})

        # Only if the berlin scenario is active, the Fog Nodes are placed with the Cell Towers
        if scenario == "berlin":
            # in 50% of the time the node is placed randomly in the area, the other times the Fog Node is at the cell tower
            decision = my_random.randint(1, 100) < 50
            node_x = my_random.randint(round(x_lower), round(
                x_upper)) if decision else node_entry["geometry"].x
            node_y = my_random.randint(round(y_lower), round(
                y_upper)) if decision else node_entry["geometry"].y
            # Calculate amount of slots depending on the settings
            slots = slots = float('inf') if unlimited_bandwidth else math.ceil(
                node_entry["Antennas"] * config["nodes"]["slot_scaler"] + 0.1)
            # Place Fog Nodes
            node = FogNode(env, id=node_id,
                           discovery_protocol=config["simulation"]["discovery_protocol"],
                           slots=slots,
                           hardware=my_random.randint(1, 1),
                           phy_x=node_x,
                           phy_y=node_y,
                           verbose=config["simulation"]["verbose"])
            env.nodes.append({"id": node_id, "obj": node})
            total_slots += slots
            # Break out of loop of max_nodes is defined and is reached
            if isinstance(max_nodes, int) and len(env.nodes) >= max_nodes:
                break

    # Placing nodes for the germany scenario
    if scenario == "germany":
        for city, coordinates in cities.items():
            node_id = uuid.uuid4()
            slots = float('inf') if unlimited_bandwidth else math.ceil(
                node_entry["Antennas"] * config["nodes"]["slot_scaler"])
            node = FogNode(env, id=node_id,
                           discovery_protocol=config["simulation"]["discovery_protocol"],
                           slots=slots,
                           hardware=my_random.randint(1, 1),
                           phy_x=coordinates[0],
                           phy_y=coordinates[1],
                           verbose=config["simulation"]["verbose"])
            env.nodes.append({"id": node_id, "obj": node})
            total_slots += slots

    print("Active Fog Nodes: {} with {} slots".format(
        len(env.nodes), total_slots))

# ------------------------------------------------------
# ------------------ Mobile Clients --------------------
# ------------------------------------------------------

    client_plans = client_data.getroot().findall('person')
    # Pre-filter all clients within the simulation area
    if scenario == "berlin":
        client_plans = list(filter(lambda client: x_lower < float(client.find('trip').attrib["x"]) < x_upper and
                                   y_lower < float(client.find('trip').attrib["y"]) < y_upper, client_plans))

    if unlimited_bandwidth and not isinstance(max_clients, int):
        warnings.warn(
            "Unlimited bandwidth and no max_clients can lead to a very high amount of clients in the simulation")

    # With unlimited bandwidth we take the max numbers of clients if defined
    # else the max amount of clients available
    if unlimited_bandwidth:
        max_clients = min(max_clients, len(client_plans)) if isinstance(
            max_clients, int) else len(client_plans)
    # With limited bandwidth we take the minimum of client ratio and max numbers of clients if defined,
    # else the client ratio
    else:
        max_clients = min(total_slots * client_ratio, max_clients) if isinstance(
            max_clients, int) else total_slots * client_ratio
        max_clients = round(max_clients)

    # Loop over clients randomly sampled from the Open Berlin Scenario until max_clients is reached
    for client_plan in my_random.sample(client_plans, max_clients):
        # A client is valid for the simulation if the scenario is for whole germany or the client is within the boundaries
        client_id = client_plan.get("id")
        client = MobileClient(env, id=client_id, plan=client_plan,
                              discovery_protocol=config["simulation"]["discovery_protocol"],
                              latency_threshold=config["clients"]["latency_threshold"],
                              roundtrip_threshold=config["clients"]["roundtrip_threshold"],
                              timeout_threshold=config["clients"]["timeout_threshold"],
                              verbose=config["simulation"]["verbose"])
        # Add client to list
        env.clients.append({"id": client_id, "obj": client})

    print("Active clients: {}, Max clients: {}".format(
        len(env.clients), max_clients))

# -----------------------------------------------------------
# ------------------ Visualization Processes for Debugging --
# -----------------------------------------------------------
    # Visualization processes to gain a better understanding of the current simulation
    # Start at runtime as pyplot graph. Only one at a time usable
    # vz_process1 = env.process(visualize_movements(env))
    # vz_process2 = env.process(visualize_latency_over_time(env, config["simulation"]["runtime"]))
    # vz_process3 = env.process(visualize_reconnections_over_time(env, config["simulation"]["runtime"]))
    # vz_process4 = env.process(unique_discovery_over_time(env, config["simulation"]["runtime"]))

# -----------------------------------------------------------
# ------------------ Run the Simulation ---------------------
# -----------------------------------------------------------
    print("Starting simulation")
    env.run(until=config["simulation"]["runtime"])

# -----------------------------------------------------------
# ------------------ Collect Metrics after Simulation -------
# -----------------------------------------------------------
    metrics_collector = Metrics(env)
    # Collecting client metrics
    client_metrics = metrics_collector.all_client()
    client_metrics = client_metrics.dropna()
    client_metrics.to_csv("Germany_Client_Metrics_{}_{}.csv".format(
        config["simulation"]["discovery_protocol"], config["clients"]["client_ratio"]))
    print(client_metrics)

    # Collecting over time metrics
    time_metrics = metrics_collector.all_time()
    time_metrics.to_csv("Germany_Time_Metrics_{}_{}.csv".format(
        config["simulation"]["discovery_protocol"], config["clients"]["client_ratio"]))
    print(time_metrics)

    # Collecting Node metrics
    node_metrics = metrics_collector.all_node()
    node_metrics.to_csv("Germany_Node_Metrics_{}_{}.csv".format(
        config["simulation"]["discovery_protocol"], config["clients"]["client_ratio"]))
    print(node_metrics)


if __name__ == "__main__":
    # execute only if run as a script
    main()
