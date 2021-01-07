import math
from .ringset import RingSet
from random import Random
import numpy as np
import pandas as pd
from scipy.spatial import ConvexHull
import warnings


class Meridian(object):
    def __init__(self, id, system_nodes, l=None, alpha=1, s=1.5, beta=0.5, max_rings = 8):
        """Meridian Node instance
        Implements the Ring Structure to form the Meridian overlay by instantiating two ring sets
        Can perform the ring membership management

        Args:
            id (uuid): uuid of the Merdidian Node
            system_nodes (int): Amount of Nodes in the system
            l (int, optional): Amount of nodes in the secondary ring.
            alpha (int, optional): Ring base. Defaults to 1.
            s (float, optional): Ring multiplier. Defaults to 1.5.
            beta (float, optional): Acceptance threshold. Defaults to 0.5.
            max_rings(int, optional): Amount of rings for both ring sets
        """
        # Radius coefficients
        self.id = id
        self.alpha = alpha
        self.s = s
        self.system_nodes = system_nodes
        # Acceptance threshold
        self.beta = beta
        # Amount of members per primary ring
        self.k = round(math.log(system_nodes, 1.6))
        # Amount of members per secondary ring
        self.l = l if l else system_nodes - self.k
        # Amount of rings in primary and secondary ringset
        self.max_rings = max_rings
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
        # ensure all nodes in the system have a full vector or the same vector as self
        for ring_number in range(1, self.max_rings+1):
            self.ring_set.freeze_ring(ring_number)
            latency_matrix = self.get_latency_matrix(ring_number)
            # Ensure there are no NaN values in the Matrix
            if latency_matrix.isnull().values.any():
                warnings.warn("Latency Matrix contains NaN values")
            # Ensure there are more than k members in the rin
            if (latency_matrix.shape[0] <= self.k + 1 and latency_matrix.shape[1] <= self.k + 1):
                # warnings.warn("Latency matrix has wrong shape, cannot perform ring replacement. Expected shape {} or bigger actual shape {}".format((self.k + 1, self.k + 1), latency_matrix.shape))
                continue
            # Ensure matrix is square
            if latency_matrix.shape[0] != latency_matrix.shape[1]:
                warnings.warn("Latency matrix is not squared",
                              latency_matrix.shape)
                continue
            # Reduce latency matrix to k elements, therefore we perform n = elements in matrix - k reduction steps
            new_primaries, new_secondaries = self.reduce_set_by_n(
                latency_matrix, n=latency_matrix.shape[0] - 1 - self.k)
            # Get all the primary members with the IDs and put them as members
            new_prim_members = []
            for prim_id in new_primaries:
                prim_member = self.ring_set.get_member(prim_id)
                if not prim_member:
                    print("primary member not found", prim_id)
                new_prim_members.append(prim_member)

            # Get all the secondary members with the IDs and put them as members
            new_second_members = []
            for sec_id in new_secondaries:
                sec_member = self.ring_set.get_member(sec_id)
                if not sec_member:
                    print("secondary member not found", sec_id)
                new_second_members.append(sec_member)

            # Set new primary and secondary members
            self.ring_set.get_ring(True, ring_number)[
                'members'] = new_prim_members
            self.ring_set.get_ring(False, ring_number)[
                'members'] = new_second_members
            self.ring_set.unfreeze_ring(ring_number)

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
        self.ring_set.insert_node(node_dict)

    def update_meridian(self, news):
        """Updates the Meridian Node with the news dictionary

        Args:
            news (dict): New dictionary from the gossip
        """
        self.ring_set.update_coordinates(
            news.get('id'), news.get('position').get_vector())

    def get_latency_matrix(self, ring_number):
        """Creates the latency matrix for a given ring

        Args:
            ring_number (int): Ring Number 

        Returns:
            DataFrame: Pandas DataFrame of the latency matrix of the given ring
        """
        # Own vector of coordinates to other members as base of the matrix
        df = self.get_vector()
        # Iterating over primary and secondary ring members
        for ring in [self.ring_set.get_ring(True, ring_number), self.ring_set.get_ring(False, ring_number)]:
            if ring.get('members'):
                for member in ring.get('members'):
                    vector = member.get('coordinates')
                    # Append vector of ring member to DataFrame
                    df = df.append(vector)
        # Remove columns from DataFrame with no data
        indices = df.index.values.tolist()
        columns = df.columns.values.tolist()
        missing = [i for i in columns if i not in indices]
        reduced_df = df.drop(columns=missing)

        return reduced_df

    def get_vector(self):
        """The coordinates of node i consist of the tuple (di1, di2, ..., dik+l), where dii = 0.

        Returns:
            DataFRame: The latency vector of the Meridian Node as Pandas DataFrame
        """
        data = {}
        # Latency to self is 0
        data[self.id] = 0
        # Getting the latency from every other node
        for ring in [*self.ring_set.primary_rings, *self.ring_set.secondary_rings]:
            for member in ring.get('members'):
                data[member.get('id')] = member.get('latency')

        df = pd.DataFrame(data=data, index=[self.id])
        return df
    
    def gram_schmidt(latency_matrix):
        """Calculates the orthonormalized vector using the gram-schmidt algorithm

        Args:
            latency_matrix (DataFrame): Pandas DataFrame of the latency matrix

        Returns:
            [tuple]: The orthonormalized vector of the latency matrix
        """
        x = latency_matrix.to_numpy()
        Q, R = np.linalg.qr(x)
        return Q
    
    def calculate_hypervolume(self, latency_matrix):
        """Calculates the hypervolume of the latency matrix polytope

        Args:
            latency_matrix (DataFrame): Pandas DataFrame of the latency matrix

        Returns:
            [float]: The hypervolume of the polytope
        """
        # gs_matrix is the latency_matrix where every row subtracts the last row in the matrix (and the last row is all 0)
        # The original C++ code is: https://github.com/infinity0/libMeridian/blob/master/Query.cpp
        gs_matrix = latency_matrix
        rows = gs_matrix.index.values.tolist()
        for row in rows:
            gs_matrix.loc[row] = gs_matrix.loc[row] - gs_matrix.loc[rows[-1]]
        gs_matrix = self.gram_schmidt(gs_matrix)
        # Now we calculate the dot product of the gs_matrix and the latency_matrix(transposed)
        dot_matrix = np.matmul(gs_matrix, latency_matrix.transpose())
        # Drop them last column for reasons
        dot_matrix = dot_matrix.drop(dot_matrix.columns[-1], axis=1)
        # And finally calculate the hypervolume
        hull = ConvexHull(dot_matrix)
        hv = hull.volume
        return hv

    def reduce_set_by_n(self, latency_matrix, n):
        """Reduces the set of k+l nodes n times until k nodes are left to set as primary nodes

        Args:
            latency_matrix (DataFrame): Pandas DataFrame of the latency matrix
            n (int): Amount of reduction steps

        Returns:
            [type]: [description]
        """
        # Go over n reducing steps
        latency_matrix = latency_matrix
        dropped_members = []
        for i in range(n):
            # Finding the "worst" member in the matrix
            # Meaning we calculate the hypervolume without the member for each member in the ring_number
            # The iteration with the highest hypervolume marks the "worst" member as the member matters the least for our HV
            worst_member = None
            maxHV = 0
            # Only do reducing steps if Dataframe does not contain NaN values
            if not latency_matrix.isnull().values.any():
                for member in latency_matrix.columns.values.tolist():
                    if member == self.id:
                        continue
                    # Remove member from latency matrix by dropping both its column and row
                    curr_lm = latency_matrix.drop(columns=member, index=member)
                    hv = self.calculate_hypervolume(curr_lm)
                    if(hv > maxHV):
                        maxHV = hv
                        worst_member = member
            # If it contains NaN values we delete that member
            else:
                for member in latency_matrix.columns.values.tolist():
                    if latency_matrix[member].isnull().values.any():
                        worst_member = member

            # remove the member from the latency matrix
            latency_matrix = latency_matrix.drop(
                columns=worst_member, index=worst_member)
            if worst_member:
                dropped_members.append(worst_member)
        new_primaries = latency_matrix.index.values.tolist()
        # Remove self out of the primary list
        new_primaries.remove(self.id)
        return new_primaries, dropped_members
