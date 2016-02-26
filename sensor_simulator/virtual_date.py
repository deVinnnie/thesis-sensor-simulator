from datetime import datetime

class VirtualDate:
    """
    Virtual clock which indicates the simulation time.
    """
    def __init__(self, startValue):
        self.startValue = startValue
        self.value = startValue

    def get_timestamp(self):
        return datetime.utcfromtimestamp(self.value)

    def get_time_elapsed(self):
        """
        Returns the total elapsed time since the beginning of the simulation.
        """
        return self.value - self.startValue

    def tick(self):
        """
        Increments the virtual clock by one hour.
        """
        self.value += (60*60)
