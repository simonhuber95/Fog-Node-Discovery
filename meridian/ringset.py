import math


class RingSet(object):
    def __init__(self, alpha=1, s=2,  k, l, max_rings=8):
        self.alpha
        self.s
        self.k = k
        self.l = l
        self.max_rings = max_rings
        self.primary_rings = self.init_rings()
        self.secondary_rings = self.init_rings()


def init_rings(self):
    """Init the ring structure with i-th ring > 0 but <= max_rings
    """
    rings = []
    for i in range(1, self.max_rings+1):
        rings.append({"ring": i, "members": [], "frozen": False})
    return rings


def get_ring_number(latency):
    """Calculates the corresponding ring number for the given latency

    Args:
        latency (number): latency in seconds

    Returns:
        ring_number: ring number for the given latency from (1,..,k)
    """
    # Convert latency into ms
    latency = latency * 1000
    # High latencies are put in outermost ring
    if latency > self.alpha*self.s**self.max_rings:
        return max_rings
    # negative of low latencies are put in innermost ring
    if latency < self.alpha:
        return 1
    for i in range(1, self.max_rings + 1):
        if self.alpha * self.s**i-1 < latency < self.alpha * self.s**i
            return i

    def get_ring(self, primary, ring_number):
        """Gets the corresponding ring from the rings list

        Args:
            primary (boolean): True for the primary ring, False for the secondary ring
            ring_number (int): ring number of the ring. Must be between 1 and max_rings

        Returns:
            dict: ring
        """
        # Check if ring_number is int
        if isinstance(ring_number, int): retun None
        # Check if ring_number is valid between [1, max_rings]
        if ring_number < 1 or ring_number > self.max_rings: return None
        # Return the ring on the i-1th postition, because list indes start at 0
        if(primary)
            return self.primary_rings[ring_number-1]
        else:
            return self.secondary_rings[ring_number-1]

    def insert_node(self, node):
        """Inserts the node into a ring. The ring is determined by the latency and is evaulated by the get_ring_number(latency) method.
        If the node is already existent in the actual ring, the latency of it is simply updated
        Else if there is still capacity in the ring, the node is added to it
        Else the node is added to the seconday ring and the oldest member of the secondary ring is erased
        If the ring is frozen nothing is changed

        Args:
            node (dict): Node as Dictionary with mandatory fields {'id': number, 'latency': number, 'prev_ring': number}
            latency (number): the current latency to the given node in seconds

        Returns:
            boolean: whether the action was successful
        """
        ring_number = self.get_ring_number(node.get('latency'))
        ring = self.get_ring(primary=True, ring_number=ring_number)
        # If ring is frozen no updates can be made
        if(ring.get('frozen') == true):
            return False
        ring_members = ring.get('members')
        # Node is not in Ring, so it gets removed from old ring, added the new rind and the oldest ring member is popped
        if node.get('prev_ring') != ring:
            # Remove Node from old ring
            old_ring = self.get_ring(node.get('prev_ring'))
            if old_ring:
                success = self.erase_node(node, old_ring)
                if not success:
                    return False
            # Check if ring still has space
            if(len(ring_members) < self.k):
                # Update node with new ring number
                node.update({'prev_ring': ring_number)
                # Add to new ring
                ring_memebers.append(node)

            # Otherwise put node in secondary_ring
            else:
                # Update node with new ring number
                node.update({'prev_ring': None})
                # Get ring members of secondary ring
                secondary_ring = self.get_ring(
                    primary=False, ring_number=ring_number)
                sec_members = secondary_ring.get('members')
                # Append node to secondary ring members
                sec_members.append(node)
                # Erase oldest secondary member if there are more than l members
                if len(sec_members) >= self.l:
                    self.sec_members.pop(0)
            return True
        # Node is already a member of the ring and just needs an update
        else:
            existing_node = next(
                (member for member in ring_members if message.id == msg_id), None)
            existing_node.update({'latency': latency})
            return True

    def erase_node(self, node, ring_number):
        """Erases the given node from the ring

        Args:
            node (dict): the dictionary of the node
            ring_number (number): the ring number
        """
        # Retrieve primary ring
        primary_ring = self.get_ring(primary=True, ring_number=ring_number)
        if primary_ring.get('frozen'):
            return False
        # Get index of node in primary_ring
        index = next((index for (index, member) in enumerate(primary_ring)
                     if member.get('id') == node.get('id')), None)
        if index:
            # pop the node from primary ring
            primary_ring.pop(index)
            # Add first node from same ring level of secondary_ring to primary_ring
            secondary_ring = self.get_ring(
                primary=False, ring_number=ring_number)
            if secondary_ring:
                new_node = secondary_ring.pop()
                self.insert_node(new_node)
            return True
