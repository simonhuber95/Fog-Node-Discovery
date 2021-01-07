import math


class RingSet(object):
    def __init__(self, k, l, alpha=1, s=2, max_rings=8):
        self.alpha = alpha
        self.s = s
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

    def get_ring_number(self, latency):
        """Calculates the corresponding ring number for the given latency

        Args:
            latency (number): latency in seconds

        Returns:
            ring_number: ring number for the given latency from (1,..,max_rings)
        """
        # Convert latency into ms
        latency = latency * 1000
        # High latencies are put in outermost ring
        if latency > self.alpha*(self.s**self.max_rings):
            return self.max_rings
        # negative or low latencies are put in innermost ring
        if latency < self.alpha:
            return 1
        for i in range(1, self.max_rings + 1):
            if (self.alpha * (self.s**(i-1))) <= latency < (self.alpha * (self.s**i)):
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
        if not isinstance(ring_number, int):
            raise TypeError(
                "Expected type: int, received Type: {}".format(type(ring_number)))
        # Check if ring_number is valid between [1, max_rings]
        if ring_number < 1 or ring_number > self.max_rings:
            raise ValueError('ring_number must be between 1 and {}, received {}'.format(
                self.max_rings, ring_number))
        # Return the ring on the i-1th postition, because list indes start at 0
        if(primary):
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

        Returns:
            boolean: whether the action was successful
        """
        ring_number = self.get_ring_number(node.get('latency'))
        ring = self.get_ring(primary=True, ring_number=ring_number)
        # If ring is frozen no updates can be made
        if(ring.get('frozen')):
            return False
        ring_members = ring.get('members')
        # Node is not in Ring, so it gets removed from old ring, added the new ring and the oldest ring member is popped
        if node.get('prev_ring') != ring_number:
            # Node gets only removed from old ring, if it has an old ring
            if node.get('prev_ring'):
                # Remove Node from old ring
                success = self.erase_node(node, node.get('prev_ring'))
                if not success:
                    return False
            # Check if ring still has space
            if(len(ring_members) < self.k):
                # Update node with new ring number
                node.update({'prev_ring': ring_number})
                # Add to new ring
                ring_members.append(node)
                return True

            # Otherwise put node in secondary_ring
            else:
                # Update node with new ring number
                node.update({'prev_ring': ring_number})
                # Get ring members of secondary ring
                secondary_ring = self.get_ring(
                    primary=False, ring_number=ring_number)
                sec_members = secondary_ring.get('members')
                # Append node to secondary ring members
                sec_members.append(node)
                # Erase oldest secondary member if there are more than l members
                if len(sec_members) >= self.l:
                    sec_members.pop(0)
                return True
        # Node is already a member of the ring and just needs an update
        else:
            if self.is_member_in_ring(node.get('id'), True, ring_number):
                existing_node = next(
                    (member for member in ring_members if member.get('id') == node.get('id')), None)
                existing_node.update({'latency': node.get(
                    'latency'), 'coordinates': node.get('coordinates')})
                return True

            if self.is_member_in_ring(node.get('id'), False, ring_number):
                secondary_ring_members = self.get_ring(
                    primary=False, ring_number=ring_number).get('members')
                existing_node = next(
                    (member for member in secondary_ring_members if member.get('id') == node.get('id')), None)
                existing_node.update({'latency': node.get(
                    'latency'), 'coordinates': node.get('coordinates')})
                return True
            return False

    def erase_node(self, node, ring_number):
        """ If node is member of primary ring the node is erased from it and adds a member from the secondary ring if there are any
        If Node is member of secondary ring it simply get erased

        Args:
            node (dict): the dictionary of the node
            ring_number (number): the ring number
        """
        # If node is member of primary ring delete it from ring and add member from secondary ring
        if self.is_member_in_ring(node.get('id'), True, ring_number):
            # Retrieve primary ring
            primary_ring = self.get_ring(primary=True, ring_number=ring_number)
            if primary_ring.get('frozen'):
                # raise Warning("Removal Failed: Primary Ring is frozen")
                return False
            # Get index of node in primary_ring
            index = next((index for (index, member) in enumerate(primary_ring.get('members'))
                          if member.get('id') == node.get('id')), None)
            if isinstance(index, int):
                # pop the node from primary ring members
                primary_ring.get('members').pop(index)
                # Add first node from same ring level of secondary_ring to primary_ring
                secondary_ring = self.get_ring(
                    primary=False, ring_number=ring_number)
                if secondary_ring.get('members'):
                    new_node = secondary_ring.get('members').pop()
                    primary_ring.get('members').append(new_node)
                return True
            else:
                raise Warning(
                    "Removal Failed: No index for primary ring found")
                return False

        # If node is member of secondary ring delete it from ring
        elif self.is_member_in_ring(node.get('id'), False, ring_number):
            # Retrieve primary ring
            secondary_ring = self.get_ring(
                primary=False, ring_number=ring_number)

            # Get index of node in primary_ring
            index = next((index for (index, member) in enumerate(secondary_ring.get('members'))
                          if member.get('id') == node.get('id')), None)
            if isinstance(index, int):
                # pop the node from secondaryring members
                secondary_ring.get('members').pop(index)
                return True
            else:
                raise Warning(
                    "Removal Failed: No index for secondary ring found")
                return False
        # Node isn't member of primary or secondary
        else:
            raise Warning("Node isnt member of any ring")
            return False

    def freeze_ring(self, ring_number):
        """Sets the 'frozen' value of the ring to True

        Args:
            ring_number (int): number of the ring to be frozen
        """
        ring = self.get_ring(primary=True, ring_number=ring_number)
        if ring:
            ring.update({'frozen': True})

    def unfreeze_ring(self, ring_number):
        """Sets the 'frozen' value of the ring to False

        Args:
            ring_number (int): number of the ring to be unfrozen
        """
        ring = self.get_ring(primary=True, ring_number=ring_number)
        if ring:
            ring.update({'frozen': False})

    def is_ring_full(self, primary, ring_number):
        """Checks if a given ring is full, meaning the amount of members in the ring is equal to k or l respectively of primary or secondary ring.

        Args:
            primary (boolean): True if primary ring, False if seconday ring
            ring_number (int): Number of the ring

        Returns:
            boolean: Whether or not the ring is full
        """
        ring = self.get_ring(primary=primary, ring_number=ring_number)
        if primary:
            return len(ring.get('members')) >= self.k
        else:
            return len(ring.get('members')) >= self.l

    def is_ring_empty(self, primary, ring_number):
        """Checks if a given ring is empty

        Args:
            primary (boolean): True if primary ring, False if seconday ring
            ring_number (int): Number of the ring

        Returns:
            boolean: Whether or not the ring is empty
        """
        ring = self.get_ring(primary=primary, ring_number=ring_number)
        return len(ring.get('members')) == 0

    def eligible_for_replacement(self, ring_number):
        """Checks if a ring is eliglible for replacement. Is True if the primary ring is full and the secondary is not empty

        Args:
            ring_number (int): Number of the ring

        Returns:
            boolean: Whether or not the ring is eligible for replacement
        """
        ring = self.get_ring(primary=True, ring_number=ring_number)
        if ring.get('frozen'):
            return False
        elif ring_number >= self.max_rings:
            return False
        elif self.is_ring_full(True, ring_number) and not self.is_ring_empty(False, ring_number):
            return True
        else:
            return False

    def get_number_of_rings(self):
        """Get how many rings the RingSet has for both primary and secondary rings

        Returns:
            int: Number of rings in the RingSet
        """
        return len(self.primary_rings)

    def swap_ring_members(self, ring_number):
        """Swaps all the members of the primary ring with the members of the secondary ring

        Args:
            ring_number (int): Number of the ring

        Returns:
            boolean: whether swap was successful
        """
        # Retrieve primary ring
        primary_ring = self.get_ring(primary=True, ring_number=ring_number)
        if primary_ring.get('frozen'):
            return False

        secondary_ring = self.get_ring(primary=False, ring_number=ring_number)
        # Exchanging the primary members with the first k secondary members
        for index in range(self.k):
            if secondary_ring.get('members'):
                # Pop old primary member
                primary_ring.get('member').pop()
                # Insert new secondary member to primary
                new_node = secondary_ring.get('members').pop()
                self.insert_node(new_node)
        return True

    def is_member_in_ring(self, member_id, primary, ring_number):
        """Checks if member is in the ring

        Args:
            member_id (ID): ID of the member
            primary (boolean): True for primary ring, false for secondary ring
            ring_number (int): Number of the ring

        Returns:
            boolean: Whether or not the given member_id exists in the ring
        """
        member_list = self.get_ring(primary, ring_number).get('members')
        return any(member.get('id') == member_id for member in member_list)

    def get_member(self, member_id):
        """Gets a member of the ringset by its ID

        Args:
            member_id (uuid): ID of the member

        Returns:
            [dict]: Dictionary of the ring member
        """
        flat_members_list = self.get_all_members()
        if flat_members_list:
            # Get the member
            return next((member for member in flat_members_list if member.get('id') == member_id), None)
        return None

    def get_all_members(self):
        """Gets all members of the ring set

        Returns:
            [List]: List of dictionaries of all members
        """
        rings = [ring for ring in [*self.primary_rings, *
                                   self.secondary_rings] if len(ring.get('members')) > 0]
        # Get all the members from the rings
        members_list = [ring.get('members') for ring in rings]
        # Flatten the list
        members_list = [item for sublist in members_list for item in sublist]
        return members_list

    def update_coordinates(self, member_id, coordinates):
        """Updates the coordinates of the given member

        Args:
            member_id (uuid): ID of the member
            coordinates (DateFrame): Pandas DataFrame of the coordinates as vector
        """
        member = self.get_member(member_id)
        if member:
            member.update({'coordinates': coordinates})
