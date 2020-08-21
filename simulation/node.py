class FogNode(object):
    def __init__(self, env):
        self.env = env
      # Start the run process everytime an instance is created.
        self.action = env.process(self.run())

    def run(self):
        while True:
            print('I am a fog node')
            yield self.env.timeout(5)
