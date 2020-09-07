import simpy
from client import MobileClient
from node import FogNode
import xml.etree.ElementTree as et

client_path = "./data/berlin-v5.4-1pct.plans.xml"
amount_clients = 1
amount_nodes = 1


# Init Environment
print("Init Environment")
env = simpy.Environment()
env.clients = []
env.nodes = []

# Getter for the network
env.getNode = lambda node_id: next((node for node in env.nodes if node["node_id"] == node_id), None)
env.getClient = lambda client_id: next((client for client in env.clients if client["client_id"] == client_id), None)

# Reading Clients from Open Berlin Scenario XML
client_data = et.parse(client_path)


print("Init Fog Nodes")
for node_id in range(1, amount_nodes+1):
    node = FogNode(env, id=node_id, discovery_protocol={}, slots=1)
    env.nodes.append({"node_id": node_id, "node": node})
print("Test node-finder: {}, {}".format(1, env.getNode(1)["node_id"]))
# Looping over the first x entries
print("Init Mobile Clients")
for client in client_data.getroot().findall('person')[:amount_clients]:
    client_id = client.get("id")
    client_plan = client.find("plan")
    client = MobileClient(env, id=client_id, plan=client_plan)
    env.clients.append({"client_id": client_id, "client": client})

# Run Simulation
env.run(until=10)
