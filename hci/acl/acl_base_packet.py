"""
    define the ACL base packet class
"""

class ACLBasePacket:
    """
        ACL base packet class
    """
    def __init__(self, packet_type: int, packet_data: bytes):
        self.packet_type = packet_type
        self.packet_data = packet_data