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


def get_participant(id):
    """
    Getter for all participants in the network
    Parameter ID as string
    Returns the participant object for the given ID
    """
    return next((elem for elem in [*env.clients, *env.nodes] if elem["id"] == id), None)["obj"]


def get_random_node():
    """
    Returns ID of random fog node
    """
    return random.choice(env.nodes)["id"]


def send_message(send_id, rec_id, msg, msg_type=1, msg_id=None):
    """
    Parameter send_id as string: ID of sender
    Paramater rec_id as string: ID of recipient
    Parameter msg as string: Message to be send
    Parameter msg_type as int *optional: type of message -> 1: regular message (default), 2: Closest node request, 3: Node discovery
    Parameter msg_id as uuid *optional: unique id of the message, if none is given a new uuid is created
    Not complete. env.timeout() is not working for some reason, so the delay has to be awaited at recipient
    """
    # Create new message ID if none is given
    if not msg_id:
        msg_id = uuid.uuid4()
    # get the latency between the two participants
    latency = env.getLatency(send_id, rec_id)
    # yield env.timeout(latency)
    # Assemble message
    message = {"msg_id": msg_id, "send_id": send_id, "rec_id": rec_id,
               "timestamp": env.now, "msg": msg, "msg_type": msg_type, "latency": latency}
    # Send message to receiver
    env.getParticipant(rec_id).msg_pipe.put(message)
    # Return messsage to sender to put it into the history
    return message


def get_latency(send_id, rec_id):
    """
    Parameter send_id as string: ID of sender
    Paramater rec_id as string: ID of recipient
    Returns float: Latency in seconds
    """
    sender = env.getParticipant(send_id)
    receiver = env.getParticipant(rec_id)
    distance = env.getDistance(
        sender.phy_x, sender.phy_y, receiver.phy_x, receiver.phy_y)
    # High-Band 5G
    if(distance < config["bands"]["5G-High"]["distance"]):
        return config["bands"]["5G-High"]["latency"]/1000 * random.randint(75, 125)/100
    # Medium-Band 5G
    elif (distance < config["bands"]["5G-Medium"]["distance"]):
        return config["bands"]["5G-Medium"]["latency"]/1000 * random.randint(75, 125)/100
    # Low-Band 5G
    elif (distance < config["bands"]["5G-Low"]["distance"]):
        return config["bands"]["5G-Low"]["latency"]/1000 * random.randint(75, 125)/100
    # 3G
    else:
        return 1


def get_distance(send_x, send_y, rec_x, rec_y):
    distance = math.sqrt((rec_x - send_x)**2 + (rec_y - send_y)**2)
    return distance


def get_boundaries(x_trans, y_trans, method="center"):
    # random method
    if(method == "random"):
        x_lower = random.randrange(
            int(config["map"]["x_min"]), int(config["map"]["x_max"]))
        y_lower = random.randrange(
            int(config["map"]["y_min"]), int(config["map"]["y_max"]))
    # center method
    elif(method == "center"):
        x_lower = int((config["map"]["x_min"] +
                       config["map"]["x_max"])/2 - x_trans/2)
        y_lower = int((config["map"]["y_min"] +
                       config["map"]["y_max"])/2 - y_trans/2)
    x_upper = x_lower + x_trans
    y_upper = y_lower + y_trans

    return((x_lower, x_upper, y_lower, y_upper))


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
# env = simpy.Environment()
# env.clients = []
# env.nodes = []
env = FogEnvironment(config)

# Assign functions to Environment Object
# env.getParticipant = get_participant
# env.getRandomNode = get_random_node
# env.sendMessage = send_message
# env.getLatency = get_latency
# env.getDistance = get_distance
# env.getBoundaries = get_boundaries

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
