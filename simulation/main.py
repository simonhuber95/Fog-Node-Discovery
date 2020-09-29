import simpy
from client import MobileClient
from node import FogNode
import xml.etree.ElementTree as et
import uuid
import random
import math
import geopandas
import matplotlib.pyplot as plt

client_path = "./data/berlin-v5.4-1pct.plans.xml"
map_path = "./data/berlin-latest-free/gis_osm_places_a_free_1.shp"
amount_clients = 1
amount_nodes = 1


# Init Environment
print("Init Environment")
env = simpy.Environment()
env.clients = []
env.nodes = []


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


def send_message(send_id, rec_id, msg, msg_type=1, msg_id = None):
    """
    Parameter send_id as string: ID of sender
    Paramater rec_id as string: ID of recipient
    Parameter msg as string: Message to be send
    Parameter msg_type as int *optional: type of message -> 1: regular message (default), 2: Closest node request, 3: Node discovery

    Not complete. env.timeout() is not working for some reason, so the delay has to be awaited at recipient
    """
    # Create new message ID if none is given
    if not msg_id:
        msg_id = uuid.uuid4()
    
    latency = env.getLatency(send_id, rec_id)
    # yield env.timeout(latency)
    message = {"msg_id": msg_id, "send_id": send_id, "rec_id": rec_id, "timestamp": env.now, "msg": msg, "msg_type": msg_type, "latency": latency}
    env.getParticipant(rec_id).msg_pipe.put(message)
    return message


def get_latency(send_id, rec_id):
    """
    Parameter send_id as string: ID of sender
    Paramater rec_id as string: ID of recipient
    Returns float: Latency in seconds
    """
    sender = env.getParticipant(send_id)
    receiver = env.getParticipant(rec_id)
    # distance = math.sqrt((receiver.phy_x - sender.phy_x)**2 + (receiver.phy_y - sender.phy_y)**2)

    return random.randint(0, 100)/100


# Assign functions to Environment Object
env.getParticipant = get_participant
env.getRandomNode = get_random_node
env.sendMessage = send_message
env.getLatency = get_latency
# Message interface for Nodes and clients


def test(send_id, rec_id, msg): return env.getParticipant(
    rec_id).msg_pipe.put({"send_id": send_id, "msg": msg})


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

# Run Simulation
# env.run(until=30)

gdf = geopandas.read_file(map_path)
print(gdf.head())
gdf.plot()
plt.savefig("test")
