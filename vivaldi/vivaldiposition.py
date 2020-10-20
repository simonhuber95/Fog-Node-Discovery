from heightcoodinates import HeightCoordinates

CONVERGE_EVERY = 5
CONVERGE_FACTOR = 50
ERROR_MIN = 0.1

cc = 0.25
ce = 0.5
initial_error = 10


class VivaldiPosition(object):
    """
    docstring
    """

    def __init__(self, coords):
    	if not isinstance(coords, HeightCoordinates):
			throw TypeError('Argument 1 must be a HeightCoordinates');

		self._coordinates = coords
		self._error = initial_error
		self._nbUpdates = 0
