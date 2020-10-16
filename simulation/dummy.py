import random
import simpy


class Dummy(object):
    def __init__(self, env):
        self.env = env
        self.out_process = self.env.process(self.out_connect())
        self.in_process = self.env.process(self.in_connect())
        self.move_process = self.env.process(self.move())
        self.monitor_process = self.env.process(self.monitor())
        self.stop_event = env.event()

    def out_connect(self):
        try:
            while True:
                print("Out Connect")
                yield self.env.timeout(random.randrange(10, 50)/10)
        except simpy.Interrupt as interrupt:
            print(interrupt.cause)

    def in_connect(self):
        try:
            while True:
                print("In Connect")
                yield self.env.timeout(random.randrange(10, 50)/10)
        except simpy.Interrupt as interrupt:
            print(interrupt.cause)

    def move(self):
        
        while True:
            print("move")
            if self.env.now > 15:
                self.stop_event.succeed("stopping manually")
                self.stop_event = self.env.event()
            try:
                yield self.env.timeout(random.randrange(10, 50)/10)
            except simpy.Interrupt as interrupt:
                print(interrupt.cause)
                break

    def stop(self, cause):
        if(self.out_process.is_alive):
            self.out_process.interrupt(cause)
        if(self.in_process.is_alive):
            self.in_process.interrupt(cause)
        if(self.move_process.is_alive):
            self.move_process.interrupt(cause)

    def monitor(self):
        cause = yield self.stop_event
        self.stop(cause)
