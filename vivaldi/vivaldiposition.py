from .heightcoodinates import HeightCoordinates
import collections
import random
import math

CONVERGE_EVERY = 5
CONVERGE_FACTOR = 50
ERROR_MIN = 0.1

cc = 0.25
ce = 0.5
initial_error = 10


class VivaldiPosition(object):

    def __init__(self, coords):
        if not isinstance(coords, HeightCoordinates):
            raise TypeError('Argument 1 must be a HeightCoordinates')

        self._coordinates = coords
        self._error = initial_error
        self._nbUpdates = 0

    def getCoordinates(self):
        """Getter for VivaldiPosition coordinates

        Returns:
                HeightCoordinates: HeightCoordinates of the VivaldiPosition
        """
        return self._coordinates

    def getLocation(self):
        """Getter for the location of the HeightCoordinates

        Returns:
                List[x,y]: List with x and y coordinate of the HeightCoordinate
        """
        return self._coordinates.getCoordinates()

    def getErrorEstimate(self):
        """Getter for the Error Estimate

        Returns:
                float: Estimated error of the VivaldiPosition
        """
        return self._error

    def setErrorEstimate(self, e):
        """Setter for the Error Estimate

        Args:
                e (Number): Error Estimate
        """
        self._error = float(e)

    def update(self, rtt, cj, ej):
        """Calculates the update in node i from the rtt to node j, the virtual coordinates of node j and the estimated error of node j

        Args:
                rtt (number): Round-Trip-Time from node i to node j
                cj (HeightCoordinates|Float32Array|VivaldiPosition): Coordinates of node j
                ej (number): Estimate error of node j

        Returns:
                boolean: whether or not the update was succesful
        """
        # Check if cj is an Array
        if (isinstance(cj, collections.Sequence)):
            return self.update(rtt, HeightCoordinates(cj[0], cj[1], cj[2]), cj[3])

        # Check if cj is a VivaldiPosition
        if isinstance(cj, VivaldiPosition):
            return self.update(rtt, cj.getCoordinates(), cj.getErrorEstimate())

        if not valid(rtt):
            raise ValueError("Invalid rtt")
        if not cj.isValid():
            raise ValueError("Invalid coordinate")
        if not valid(ej):
            raise ValueError("Invalid error estimate")
        
        error = self._error

        # Ensure we have valid data in input
        # (clock changes lead to crazy rtt values)
        if (rtt <= 0 or rtt > 5 * 60 * 1000):
            raise ValueError("RTT out of logical bounds")
        if (error + ej == 0):
            raise ValueError("Errors to small")

        # Sample weight balances local and remote error. (1)
        w = error / (ej + error)

        # Real error
        re = rtt - self._coordinates.distance(cj)

        # Compute relative error of self sample. (2)
        es = abs(re) / rtt

        # Update weighted moving average of local error. (3)
        new_error = es * ce * w + error * (1 - ce * w)

        # Update local coordinates. (4)
        delta = cc * w
        scale = delta * re

        random_error = HeightCoordinates(
            random.random() / 10, random.random() / 10, 0)
        new_coordinates = self._coordinates.add(
            self._coordinates.sub(cj.add(random_error)).unity().scale(scale))

        if valid(new_error) and new_coordinates.isValid():
            self._coordinates = new_coordinates
            self._error = new_error if new_error > ERROR_MIN else ERROR_MIN
        else:
            self._coordinates = HeightCoordinates(0, 0, 0)
            self._error = initial_error

        if not cj.atOrigin():
            self._nbUpdates = + 1

        if self._nbUpdates > CONVERGE_EVERY:
            self._nbUpdates = 0
            self.update(10, HeightCoordinates(0, 0, 0), CONVERGE_FACTOR)

        return True

    def isValid(self):
        """Checks if the VivaldiPosition is valid

        Returns:
                boolean: whether ot not the VivaldiPosition is valid
        """
        return self._error is not None and self.getCoordinates().isValid()

    def estimateRTT(self, cj):
        """Gives an estimate of the Round-Trip-Time
        Args:
                cj (HeightCoordinates|VivaldiPosition): HeightCoordinates or VivaldiPosition to which the RTT is estimated
        Returns:
                float: RTT estimate
        """
        if isinstance(cj, HeightCoordinates):
            return self._coordinates.distance(cj)
        elif isinstance(cj, VivaldiPosition):
            coords = cj.getCoordinates()
            if coords.atOrigin() or self._coordinates.atOrigin():
                return 0

            return self._coordinates.distance(coords)
        else:
            raise TypeError(
                "HeightCoordinates or VivaldiPosition expected, received {}".format(type(cj)))

    def toFloatArray(self):
        return [self._coordinates.x, self._coordinates.y, self._coordinates.h, self._error]

    @staticmethod
    def fromFloatArray(data):
        """Creates a VivaldiPosition from a float Array

        Args:
                data (List[float]): float Array with x, y, height and error estimate

        Returns:
                VivaldiPosition: VivaldiPosition from the given data
        """
        coords = HeightCoordinates(data[0], data[1], data[2])
        pos = VivaldiPosition(coords)
        pos.setErrorEstimate(data[3])
        return pos

    @staticmethod
    def create(error=None):
        """Creates a new VivaldiPosition in the Origin

        Args:
            error (float) *Optional: Error of the VivaldiPosition

        Returns:
            VivaldiPosition: new VivaldiPosition
        """
        np = VivaldiPosition(HeightCoordinates(0, 0, 0))

        if error:
            np.setErrorEstimate(error)

        return np

    def equals(self, other):
        if isinstance(other, VivaldiPosition):
            if (other._error != self._error):
                return False

            elif not other._coordinates.equals(self._coordinates):
                return False

            else:
                return True

        else:
            return False


def valid(f):
    return math.isfinite(f)
