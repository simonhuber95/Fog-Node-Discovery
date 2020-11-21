import math
from .ringset import RingSet
from .gram_schmidt import gs
from random import Random
import numpy as np
import pandas as pd
from scipy.spatial import ConvexHull


class Meridian(object):
    def __init__(self, id, system_nodes, l=None, alpha=1, s=2, beta=0.5):
        # Radius coefficients
        self.id = id
        self.alpha = alpha
        self.s = s
        # Acceptance threshold
        self.beta = beta
        # Amount of members per primary ring
        self.k = round(math.log(system_nodes, 1.6))
        # Amount of members per secondary ring
        self.l = l if l else system_nodes - self.k
        # Amount of rings in primary and secondary ringset
        self.max_rings = 8
        self.ring_set = RingSet(
            k=self.k, l=self.l, alpha=alpha, s=s, max_rings=self.max_rings)

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

    def add_node(self, node_id, latency, coordinates):
        """Wrapper function to add a node to the Meridian system

        Args:
            node_id (uuid): ID of the node
            latency (float): latency of the node in seconds
            coordinates (list): coordinate vector of the Meridian node
        """
        prev_ring = None
        # Check if node is currently member of a primary ring
        for ring_number in range(1, self.ring_set.get_number_of_rings() + 1):
            if self.ring_set.is_member_in_ring(node_id, True, ring_number):
                prev_ring = ring_number
                break

        if not prev_ring:
            # Check if node is currently member of a secondary ring
            for ring_number in range(1, self.ring_set.get_number_of_rings() + 1):
                if self.ring_set.is_member_in_ring(node_id, False, ring_number):
                    prev_ring = ring_number
                    break
        
        node_dict = {'id': node_id, 'latency': latency,
                     'prev_ring': prev_ring, 'coordinates': coordinates}
        
        prev_shape = self.get_vector().shape
        self.ring_set.insert_node(node_dict)
        
        # if prev_shape != self.get_vector().shape:
        #     print("We altered the shape", prev_shape, self.get_vector().shape, node_dict)

    def get_latency_matrix(self):
        matrix = np.array()
        for ring in [*self.ring_set.primary_rings, *self.ring_set.secondary_rings]:
            for member in ring.get('members'):
                matrix.append(member.get('coordinates'))
        return matrix

    def get_vector(self):
        """The coordinates of node i consist of the tuple (di1, di2, ..., dik+l), where dii = 0.

        Returns:
            list: The latency vector of the Meridian Node
        """
        data = {}
        data[self.id] = 0
        for ring in [*self.ring_set.primary_rings, *self.ring_set.secondary_rings]:
            for member in ring.get('members'):
                data[member.get('id')] = member.get('latency')

        df = pd.DataFrame(data=data, index=[self.id])
        return df

    def get_volume(self, latency_matrix):
        hull = ConvexHull(latency_matrix)
        return hull.volume

    def calculate_hypervolume(self):
        latency_matrix = self.get_latency_matrix()
        # print(latency_matrix)

        gs_matrix = gs(latency_matrix)
        # print(gs_matrix)

    def reduce_set_by_n(vector, n):
        return false

    def create_latency_matrix(self):
        return false
