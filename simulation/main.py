import simpy
from client import MobileClient

env = simpy.Environment()
client = MobileClient(env)
env.run(until=15)
