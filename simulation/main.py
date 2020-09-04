import simpy
from client import MobileClient
from node import FogNode
import xml.etree.ElementTree as et

client_path = "./data/berlin-v5.4-1pct.plans.xml"
amount_clients = 1
amount_nodes = 1
clients = []
nodes = []

# Init Environment
print("Init Environment")
env = simpy.Environment()

# Reading Clients from Open Berlin Scenario XML
client_data = et.parse(client_path)

# Looping over the first x entries
print("Init Mobile Clients")
for client in client_data.getroot().findall('person')[:amount_clients]:
    client_id = client.get("id")
    client_plan = client.find("plan")
    client = MobileClient(env, id = client_id, plan = client_plan)
    clients.append(client)

print("Init Fog Nodes")
for node_id in range(1, amount_nodes+1):
    node = FogNode(env, id = node_id, discovery_protocol={}, network = {}, slots = 1)
    nodes.append(node)
    
# Run Simulation
env.run(until=2500)
