# %%

import simpy
from client import MobileClient
from node import FogNode
import visualize
import xml.etree.ElementTree as et
import uuid
import random
import math
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point
import yaml
from pathlib import Path

# Set base path of the project
base_path = Path().absolute().parent

# open the config.yaml as object
with open(base_path.joinpath("config.yml"), "r") as ymlfile:
    config = yaml.load(ymlfile, Loader=yaml.FullLoader)

# set path to the OpenBerlinScenario.xml
client_path = base_path.joinpath(config["clients"]["path"])
# set path to the map of Berlin
map_path = base_path.joinpath(config["map"]["path"])
# Set amount of client
amount_clients = config["clients"]["amount"]
# Set amount of nodes
amount_nodes = config["nodes"]["amount"]


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


def send_message(send_id, rec_id, msg, msg_type = 1, msg_id = None):
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
    print("Distance to Node: {}".format(distance))
    # High-Band 5G
    if(distance < config["bands"]["5G-High"]["distance"]):
        latency = config["bands"]["5G-High"]["latency"]/1000 * random.randint(75, 125)/100
        print("5G-High", latency)
        return latency
    # Medium-Band 5G
    elif (distance < config["bands"]["5G-Medium"]["distance"]):
        latency = config["bands"]["5G-Medium"]["latency"]/1000 * random.randint(75, 125)/100
        print("5G-Medium", latency)
        return latency
    # Low-Band 5G
    elif (distance < config["bands"]["5G-Low"]["distance"]):
        print("5G-Low")
        return config["bands"]["5G-Low"]["latency"]/1000 * random.randint(75, 125)/100
    # 3G
    else:
        return 1


def get_distance(send_x, send_y, rec_x, rec_y):
    distance = math.sqrt((rec_x - send_x)**2 + (rec_y - send_y)**2)
    return distance

# Init Environment
print("Init Environment")
env = simpy.Environment()
env.clients = []
env.nodes = []

# Assign functions to Environment Object
env.getParticipant = get_participant
env.getRandomNode = get_random_node
env.sendMessage = send_message
env.getLatency = get_latency
env.getDistance = get_distance

# Reading Clients from Open Berlin Scenario XML
client_data = et.parse(client_path)

print("Init Fog Nodes")
for i in range(1, amount_nodes+1):
    node_id = uuid.uuid4()
    node = FogNode(env, id=node_id, discovery_protocol={}, slots=1)
    env.nodes.append({"id": node_id, "obj": node})
# Looping over the first x entries
print("Init Mobile Clients")
for client in client_data.getroot().findall('person')[:amount_clients]:
    client_id = client.get("id")
    client_plan = client.find("plan")
    client = MobileClient(env, id=client_id, plan=client_plan)
    env.clients.append({"id": client_id, "obj": client})

# viz = visualize.visualize_movements(env, map_path)

# Run Simulation
env.run(until=100)


# %%
