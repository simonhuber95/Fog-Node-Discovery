import math
import simpy
import geopy


class MobileClient(object):
    def __init__(self, env, id, plan):
        self.env = env
        self.id = id
        self.phy_x = 0
        self.phy_y = 0
        self.virt_x = 0
        self.virt_y = 0
        self.plan = plan
        self.pairs = zip(plan.findall('activity'), plan.findall('leg'))

        print("Mobile client", self.id, "active")
      # Start the run process everytime an instance is created.
        self.action = env.process(self.run())

    def run(self):
        print("Client {} starting".format(self.id))
        for activity, leg in self.pairs:
            print(activity.get("type"))
            entry = {}
            entry['x'] = activity.attrib['x']
            entry['y'] = activity.attrib['y']
            route = leg.find('route')
            entry['trav_time'] = route.attrib['trav_time']
            entry['distance'] = route.attrib['distance']
            print(entry)
            yield self.env.process(self.move(entry['x'], entry['y'], entry['trav_time'], entry['distance']))

    def move(self, to_x, to_y, duration, distance):
        # velocity = math.sqrt((self.phy_x - to_x) ^ 2 + (self.phy_y - to_y) ^ 2)/duration  # in meter per tick
        vel_x = (to_x - self.phy_x) / duration
        vel_y = (to_y - self.phy_y) / duration
        while(to_x != round(self.phy_x) and round(to_y != self.phy_y)):
            self.phy_x += vel_x
            self.phy_y += vel_y

            yield self.env.timeout(1)
            print("Timestep: {} Client id: {} x:{:.2f} y:{:.2f}".format(
                self.env.now, self.id, self.phy_x, self.phy_y))
