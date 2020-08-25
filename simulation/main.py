import simpy
from client import MobileClient
from node import FogNode
import xml.etree.ElementTree as et

client_path = "./data/berlin-v5.4-1pct.plans.xml"
amount_clients = 1

# Init Environment
print("Init Environment")
env = simpy.Environment()

# Reading Clients from Open Berlin Scenario XML
client_data = et.parse(client_path)

# Looping over the first x entries
for client in client_data.getroot().findall('person')[:amount_clients]:
    client_id = client.get("id")
    client_plan = client.find("plan")
    client = MobileClient(env, client_id, client_plan)

print("Init MobileClients")
#print("Init Fog Nodes")
#node = FogNode(env)
env.run(until=15000)
