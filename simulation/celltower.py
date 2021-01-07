class Celltower(object):
    def __init__(self, env, id, phy_x=4632239.86, phy_y=5826584.42, verbose=False):
        self.env = env
        self.id = id
        self.phy_x = phy_x
        self.phy_y = phy_y
        self.verbose = verbose

        if self.verbose:
            print("Cell Tower {} active at x:{}, y: {}".format(
                self.id, self.phy_x, self.phy_y))

    def get_coordinates(self):
        """Returns the physical coordinates of the node

        Returns:
            float: x coordinate of the node in GK4/EPSG:31468
            float: y coordinate of the node in GK4/EPSG:31468
        """
        return self.phy_x, self.phy_y
