import math
import simpy


class MobileClient(object):
    def __init__(self, env, id):
        self.env = env
        self.id = id
        self.phy_x = 0
        self.phy_y = 0
        self.virt_x = 0
        self.virt_y = 0
        print("Mobile client", self.id, "active")
      # Start the run process everytime an instance is created.
        self.action = env.process(self.run())

    def run(self):
        movement = {"from": [0, 0], "to": [
            8 *self.id, 20*self.id], "duration": 10 + self.id}
        print("Client", self.id, "starts moving")
        yield self.env.process(self.move(movement.get("to")[0], movement.get("to")[1], movement.get("duration")))

    def move(self, to_x, to_y, duration):
        # velocity = math.sqrt((self.phy_x - to_x) ^ 2 + (self.phy_y - to_y) ^ 2)/duration  # in meter per tick
        vel_x = (to_x - self.phy_x) / duration
        vel_y = (to_y - self.phy_y) / duration
        while(to_x != round(self.phy_x) and round(to_y != self.phy_y)):
            self.phy_x += vel_x
            self.phy_y += vel_y

            yield self.env.timeout(1)
            print("Timestep: {} Client id: {} x:{:.2f} y:{:.2f}".format(
                self.env.now, self.id, self.phy_x, self.phy_y))
