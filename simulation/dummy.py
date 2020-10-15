import random
import simpy

class Dummy(object):
    def __init__(self, env):
        self.env = env
        self.out_process = self.env.process(self.out_connect())
        self.in_process = self.env.process(self.in_connect())
        self.move_process = self.env.process(self.move())
    
    def out_connect(self):
        print("Out Connect")
        try:
            yield self.env.timeout(random.randrange(10,50)/10)
        except simpy.Interrupt as interrupt:
            print(interrupt.cause)
        
    def in_connect(self):
        print("In Connect")
        try:
            yield self.env.timeout(random.randrange(10,50)/10)
        except simpy.Interrupt as interrupt:
            print(interrupt.cause)
        
        
    def move(self):
        print("move")
        if self.env.now > 15:
            self.stop("Manually stopping")
        try:
            yield self.env.timeout(random.randrange(10,50)/10)
        except simpy.Interrupt as interrupt:
            print(interrupt.cause)
        
        
    def stop(self, cause):
        self.out_process.interrupt(cause)
        self.in_process.interrupt(cause)
        