# %%

import simpy
from simulation.client import MobileClient
from simulation.node import FogNode
from simulation.celltower import Celltower
from simulation.metrics import Metrics
from simulation.dummy import Dummy
from simulation.fog_environment import FogEnvironment
import xml.etree.ElementTree as et
import uuid
import geopandas as gpd
import yaml
from pathlib import Path
from random import Random
import math

from simulation.visualize import *
# Set base path of the project

def main():
    # Creating a Random with a seed
    my_random = Random("Fog-Node-Discovery")
    base_path = Path().absolute()

    # open the config.yaml as object
    with open(base_path.joinpath("config.yml"), "r") as ymlfile:
        config = yaml.load(ymlfile, Loader=yaml.FullLoader)

    # set path to the OpenBerlinScenario.xml
    client_path = base_path.joinpath(config["clients"]["path"])
    # set path to the Cell Tower json
    nodes_path = base_path.joinpath(config["nodes"]["path"])
    # set path to the map of Berlin
    map_path = base_path.joinpath(config["map"]["city"])
    # set path to the roads of Berlin
    roads_path = base_path.joinpath(config["map"]["roads"])
    # Set amount of client
    max_clients = config["clients"]["max_clients"]
    # Set amount of nodes
    min_nodes = config["nodes"]["min_nodes"]

    # Init Environment
    print("Init Environment")
    env = FogEnvironment(config)

    client_data = et.parse(client_path)
    # Readinge Node coordinates from json
    nodes_gdf = gpd.read_file(nodes_path)

    while True:
        # Get boundaries of simulation
        (x_lower, x_upper, y_lower, y_upper) = env.generate_boundaries(
            config["simulation"]["area"], config["simulation"]["area"], method=config["simulation"]["area_selection"])

        print("Simulation area x: {} - {}, y: {} - {}".format(x_lower,
                                                            x_upper, y_lower, y_upper))
        # Filter Nodes withon boundary
        filtered_nodes_gdf = nodes_gdf.cx[x_lower:x_upper, y_lower:y_upper]
        env.amount_nodes = len(filtered_nodes_gdf)
        print("Nodes found:", len(filtered_nodes_gdf))
        if(len(filtered_nodes_gdf) >= min_nodes):
            env.boundaries = (x_lower, x_upper, y_lower, y_upper)
            break

    print("Init Fog Nodes")
    total_slots = 0
    for index, node_entry in filtered_nodes_gdf.iterrows():
        node_id = uuid.uuid4()
        cell_id = uuid.uuid4()
        # in 50% of the time a cell tower has a FogNode
        if my_random.randint(1,100) < 50:
            node_x = my_random.randint(round(x_lower), round(x_upper))
            node_y = my_random.randint(round(y_lower), round(y_upper))
        # the other times the node is placed randomly in the area
        else:
            node_x = node_entry["geometry"].x
            node_y = node_entry["geometry"].y
            
        node = FogNode(env, id=node_id,
                    discovery_protocol=config["simulation"]["discovery_protocol"],
                    slots=math.ceil(node_entry["Antennas"] * config["nodes"]["slot_scaler"]),
                    phy_x=node_x,
                    phy_y=node_y,
                    verbose=config["simulation"]["verbose"])
        env.nodes.append({"id": node_id, "obj": node})
        total_slots += math.ceil(node_entry["Antennas"] * config["nodes"]["slot_scaler"])
        celltower = Celltower(env, id=cell_id,
                    phy_x=node_entry["geometry"].x,
                    phy_y=node_entry["geometry"].y,
                    verbose=config["simulation"]["verbose"])
        env.celltowers.append({"id": cell_id, "obj": celltower})
        
    # Looping over the first x entries
    print("Init Mobile Clients")
    # If a max amount of clients is a number take the minimum of this and the (slots * client ratio), 
    # otherwise just the (slots * client_ratio)
    client_ratio = config["clients"]["client_ratio"]
    max_clients = min(total_slots * client_ratio, max_clients) if type(max_clients) == type(total_slots) else total_slots * client_ratio
    max_clients = round(max_clients)
    for client in client_data.getroot().iterfind('person'):
        client_plan = client.find("plan")
        if(x_lower < float(client_plan.find('activity').attrib["x"]) < x_upper and
        y_lower < float(client_plan.find('activity').attrib["y"]) < y_upper):
            client_id = client.get("id")
            client = MobileClient(env, id=client_id, plan=client_plan,
                                discovery_protocol=config["simulation"]["discovery_protocol"],
                                latency_threshold=config["clients"]["latency_threshold"],
                                roundtrip_threshold=config["clients"]["roundtrip_threshold"],
                                timeout_threshold=config["clients"]["timeout_threshold"],
                                verbose=config["simulation"]["verbose"])
            env.clients.append({"id": client_id, "obj": client})
            # Break out of loop if enough clients got generated
            if(len(env.clients) == max_clients):
                break

    print("Active clients: ", len(env.clients))

    # viz_process1 = env.process(visualize_vivaldi(env))
    vz_process2 = env.process(visualize_movements(env))
    # vz_process3 = env.process(visualize_client_performance(env, config["simulation"]["runtime"]))
    # vz_process4 = env.process(visualize_node_performance(env, config["simulation"]["runtime"]))

    # Run Simulation
    env.run(until=config["simulation"]["runtime"])
    # Printing metrics
    metrics = Metrics(env).all()
    metrics = metrics.dropna()
    metrics.to_csv("Metrics_{}_{}ms.csv".format(config["simulation"]["discovery_protocol"], config["clients"]["latency_threshold"] * 1000))
    print(metrics)

    # Metrics(env).collect_error_over_time().plot()
    # Metrics(env).collect_opt_choice_over_time().plot()


    # Reading road layout for Berlin to distribute the nodes
    # roads = gpd.read_file(roads_path)
    # roads = roads.to_crs(epsg="31468")
    # Retrieving the boundaries of Berlin
    # pd.options.display.float_format = "{:.4f}".format
    # boundaries = roads["geometry"].bounds
    # print(boundaries.min())
    # print(boundaries.max())

if __name__ == "__main__":
    # execute only if run as a script
    main()
# %%
