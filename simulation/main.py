import simpy
from client import MobileClient
from node import FogNode
import xml.etree.ElementTree as et
import uuid

client_path = "./data/berlin-v5.4-1pct.plans.xml"
amount_clients = 1
amount_nodes = 1


# Init Environment
print("Init Environment")
env = simpy.Environment()
env.clients = []
env.nodes = []

# Getter for Nodes in the network
# returns the Node object with the given ID
env.getNode = lambda node_id: next(
    (node for node in env.nodes if node["id"] == node_id), None)["obj"]

# Getter for Clients in the network
# returns the Client object with the given ID
env.getClient = lambda client_id: next(
    (client for client in env.clients if client["id"] == client_id), None)["obj"]

# Getter for all participants in the network
# returns the participant object with the given ID
env.getParticipant = lambda id: next(
    (elem for elem in [*env.clients, *env.nodes] if elem["id"] == id), None)["obj"]

# Message interface for Nodes and clients
env.sendMessage = lambda send_id, rec_id, msg: env.getParticipant(rec_id).msg_pipe.put({"sender": send_id, "msg":msg)

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
