import math

class Meridian(object):
    def __init__(self, alpha = 1, s = 2, system_nodes, beta = 0.5, l):
        self.alpha = alpha
        self.s = s
        self.beta = beta
        self.k = math.log(system_nodes, 1.6)
        self.l = l
        