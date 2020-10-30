import math
import random

MAX_X = 30000
MAX_Y = 30000
MAX_H = 30000


class HeightCoordinates(object):
    """
    Height Coordinate object used in the Vivaldi Position
    """

    def __init__(self, x, y, height):
        self.x = x
        self.y = y
        self.h = height

    def add(self, other):
        """Adds two HeightCoordinates 
        Args:
            other (HeightCoordinates): HeightCoordinates to be added
        Returns:
            HeightCoordinates: new HeightCoordinate
        """
        return primitive(self, other, 1)

    def sub(self, other):
        """Subtracts two HeightCoordinates
        Args:
            other (HeightCoordinates): HeightCoordinates to be subtracted
        Returns:
            HeightCoordinates: new HeightCoordinate
        """
        return primitive(self, other, -1)

    def scale(self, scale):
        """Scales the HeightCoordinate in each direction: x, y, h
        Returns:
            HeightCoordinates: new scaled HeightCoordinate
        """
        return HeightCoordinates(
            scale * self.x,
            scale * self.y,
            scale * self.h
        )

    def measure(self):
        """Measures the HeightCoordinate
        Returns:
            float: measure of the HeightCoordinate
        """
        return math.sqrt(self.x * self.x + self.y * self.y) + self.h

    def atOrigin(self):
        """Checks if HeightCoordinate is at the Origin (0,0)
        Returns:
            boolean: whether or not the HeightCoordinate is at the Origin
        """
        return self.x == 0 and self.y == 0

    def isValid(self):
        """Checks if the HeightCoordinate is valid
        Returns:
            boolean: whether or not the HeightCoordinate is valid
        """
        return valid(self.x) and valid(self.y) and valid(self.h) and abs(self.x) <= MAX_X and abs(self.y) <= MAX_Y and abs(self.h) <= MAX_H

    def distance(self, other):
        """[summary]
        Args:
            other (HeightCoordinates): HeightCoordinate to which the distance is calculated
        Returns:
            float: distance between the two HeightCoordinates
        """
        return self.sub(other).measure()

    def unity(self):
        """ I actually dont know what this really does

        Returns:
            HeightCoordinates: a new scaled HeightCoordinate
        """
        measure = self.measure()

        if not measure:
            # Special Vivaldi Case, when u(0) = random unity vector
            return HeightCoordinates(
                random.random,
                random.random(),
                random.random()).unity()

        return self.scale(1 / measure)

    def getCoordinates(self):
        """Gets the coordinated of the HeightCoordinate
        Returns:
            list[x,y]: coordinates of the HeightCoordinate
        """
        return [self.x, self.y]

    def equals(self, other):
        """Checks if two HeightCoordinates have the some coordinates

        Args:
            other (HeightCoordinate): HeightCoordinate to be compared to

        Returns:
            boolean: Wheter or not the two HeightCoordinates have equal coordinates
        """
        if isinstance(other, HeightCoordinates):
            if (other.x != self.x or other.y != self.y or other.h != self.h):
                return False

            return True

        return False


def valid(f):
    """Checks if the given coordinate is valid
    Args:
        f (float): Coordinate of a HeightCoordinate

    Returns:
        boolean: whether or not the coordinate is valid
    """
    return math.isfinite(f)


def primitive(c1, c2, scale):
    """Collects the two HeightCoordinates and executes the given scale
    Args:
        c1 (HeightCoordinates): HeightCoordinate to be transformed
        c2 (HeightCoordinates): HeightCoordinate to be transformed
        scale (integer): scale to be performed on HeightCoordinates

    Returns:
        HeightCoordinates: new scaled HeightCoordinate
    """
    return HeightCoordinates(
        c1.x + c2.x * scale,
        c1.y + c2.y * scale,
        abs(c1.h + c2.h)
    )
