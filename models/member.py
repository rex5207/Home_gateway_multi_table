class Member:
    def __init__(self, mac):
        """Initial Setting methid."""
        self.port = None
        self.mac = mac
        self.ip = None
        self.hostname = None
        self.datapath = None
        self.meter_id = None
