import math
from .ringset import RingSet
from random import Random

class Meridian(object):
    def __init__(self, system_nodes, alpha=1, s=2, beta=0.5):
        # Radius coefficients
        self.alpha = alpha
        self.s = s
        # Acceptance threshold
        self.beta = beta
        # Amount of members per primary ring
        self.k = math.log(system_nodes, 1.6)
        # Amount of members per secondary ring
        self.l = 1.5 * self.k
        # Amount of rings in primary and secondary ringset
        self.max_rings = 8
        self.ring_set = RingSet(
            alpha=alpha, s=s,  k=self.k, l=l, max_rings=self.max_rings)

    def perform_ring_management(self):
        """Meridian achieves geographic diversity by periodically reassessing ring membership decisions 
        and replacing ring members with alternatives that provide greater diversity. 
        Within each ring, a Meridian node not only keeps track of the k primary ring members, 
        but also a constant number l of secondary ring members, which serve as a FIFO pool of candidates for primary ring membership

        Returns:
            boolean: Whether or not the action was succesful
        """
        # Find all full primary rings with non empty secondaries
        eligible_rings = []
        for ring_number in range(1, self.ring_set.get_number_of_rings()+1):
            if self.ring_set.eligible_for_replacement(ring_number):
                eligible_rings.append(ring_number)
        
        if not eligible_rings:
            return False
        
        selected_ring = Random.choice(eligible_rings)
        # swap members of primary ring if there is a replacement in secondary ring
        self.ring_set.swap_ring_members(selected_ring)
    
    def add_node(self, node_id, latency):
        """Wrapper function to add a node to the Meridian system

        Args:
            node_id (uuid): ID of the node
            latency (float): latency of the node in seconds
        """
        node_dict = {'id': node_id, 'latency': latency, 'prev_ring': None}
        self.ring_set.insert_node(node_dict)
            
    def calculate_hypervolume(self):
    
    def reduce_set_by_n(vector, n):
        
    def create_latency_matrix(self):
    
