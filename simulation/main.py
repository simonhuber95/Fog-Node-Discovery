import simpy
from client import MobileClient
from node import FogNode

amount_clients = 1
print("Init Environment")
env = simpy.Environment()
print("Init MobileClients")
for i in range(1, amount_clients+1):
    client = MobileClient(env, i)
#print("Init Fog Nodes")
#node = FogNode(env)
env.run(until=20)