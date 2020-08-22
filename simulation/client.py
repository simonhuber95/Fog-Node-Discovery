class MobileClient(object):
    def __init__(self, env):
        self.env = env
      # Start the run process everytime an instance is created.
        self.action = env.process(self.run())
        self.phy_x = 0
        self.phy_y = 0
        self.virt_x = 0
        self.virt_y = 0

    def run(self):
        movement = {"from": [0, 0], "to": [8, 20], "duration": 10}
        while True:
            print('Start parking and charging at %d' % self.env.now)
            yield self.env.timeout(1)
