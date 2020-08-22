import simpy
from client import MobileClient
from node import FogNode

env = simpy.Environment()
client = MobileClient(env)
node = FogNode(env)
env.run(until=15)
