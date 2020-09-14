import simpy
from client import MobileClient
from node import FogNode
import xml.etree.ElementTree as et
import uuid
import random

client_path = "./data/berlin-v5.4-1pct.plans.xml"
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


def send_message(send_id, rec_id, msg):
    """
    Parameter send_id as string: ID of sender
    Paramater rec_id as string: ID of recipient
    Parameter msg as string: Message to be send
    """
    env.getParticipant(rec_id).msg_pipe.put({"send_id": send_id, "msg": msg})


# Assign functions to Environment Object
env.getParticipant = get_participant
env.getRandomNode = get_random_node
env.sendMessage = send_message
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
env.run(until=10)
