# %%

import simpy
from simulation.client import MobileClient
from simulation.node import FogNode
from simulation.metrics import Metrics
from simulation.dummy import Dummy
from simulation.fog_environment import FogEnvironment
import simulation.visualize
import xml.etree.ElementTree as et
import uuid
import random
import math
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from shapely.geometry import Point, Polygon
import yaml
from pathlib import Path

# Set base path of the project
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
    (x_lower, x_upper, y_lower, y_upper) = env.get_boundaries(
        config["simulation"]["area"], config["simulation"]["area"], method=config["simulation"]["area_selection"])

    print("Simulation area x: {} - {}, y: {} - {}".format(x_lower,
                                                          x_upper, y_lower, y_upper))
    # Filter Nodes withon boundary
    filtered_nodes_gdf = nodes_gdf.cx[x_lower:x_upper, y_lower:y_upper]
    print("Nodes found:", len(filtered_nodes_gdf))
    if(len(filtered_nodes_gdf) >= min_nodes):
        env.boundaries = (x_lower, x_upper, y_lower, y_upper)
        break

print("Init Fog Nodes")
for index, node_entry in filtered_nodes_gdf.iterrows():
    node_id = uuid.uuid4()
    node = FogNode(env, id=node_id,
                   discovery_protocol={},
                   slots=node_entry["Antennas"],
                   phy_x=node_entry["geometry"].x,
                   phy_y=node_entry["geometry"].y,
                   verbose=config["simulation"]["verbose"])
    env.nodes.append({"id": node_id, "obj": node})
# Looping over the first x entries
print("Init Mobile Clients")


for client in client_data.getroot().iterfind('person'):
    client_plan = client.find("plan")
    if(x_lower < float(client_plan.find('activity').attrib["x"]) < x_upper and
       y_lower < float(client_plan.find('activity').attrib["y"]) < y_upper):
        client_id = client.get("id")
        client = MobileClient(env, id=client_id, plan=client_plan,
                              latency_threshold=config["clients"]["latency_threshold"],
                              roundtrip_threshold=config["clients"]["roundtrip_threshold"],
                              timeout_threshold=config["clients"]["timeout_threshold"],
                              verbose=config["simulation"]["verbose"])
        env.clients.append({"id": client_id, "obj": client})
        # Break out of loop if enough clients got generated
        if(not max_clients and len(env.clients) == max_clients):
            break

# visualize.visualize_movements(env, map_path)


# add dummy
# dummy = Dummy(env)

# Run Simulation
env.run(until=config["simulation"]["runtime"])
# Printing metrics
print(Metrics(env).all())


# Reading road layout for Berlin to distribute the nodes
# roads = gpd.read_file(roads_path)
# roads = roads.to_crs(epsg="31468")
# Retrieving the boundaries of Berlin
# pd.options.display.float_format = "{:.4f}".format
# boundaries = roads["geometry"].bounds
# print(boundaries.min())
# print(boundaries.max())


# %%
