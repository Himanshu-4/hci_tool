""" 
    Hci utility functions 
    Contains function for address conversion and other utilities
    to generate random addresses, check public, random, or static addresses.
"""

import random
from typing import Optional, Union



# create the lib for handling address stuff, create address from string, check if address is public, random or static


class AddressUtil:
    """Utility class for handling Bluetooth addresses"""

    @staticmethod
    def generate_random_address() -> str:
        """Generate a random Bluetooth address"""
        return ':'.join(f'{random.randint(0, 255):02x}' for _ in range(6))

    @staticmethod
    def is_public_address(address: str) -> bool:
        """Check if the address is a public address"""
        return address[0] != '0' and address[1] != '0'

    @staticmethod
    def is_random_address(address: str) -> bool:
        """Check if the address is a random address"""
        return address[0] == '0' or address[1] == '0'

    @staticmethod
    def is_static_address(address: str) -> bool:
        """Check if the address is a static address"""
        return AddressUtil.is_random_address(address) and not AddressUtil.is_public_address(address)

    @staticmethod
    def bd_addr_bytes_to_str(bd_addr_bytes: bytes) -> str:
        """Convert BD_ADDR bytes to string"""
        if len(bd_addr_bytes) != 6:
            raise ValueError("BD_ADDR must be 6 bytes long")
        return ':'.join(f'{byte:02x}' for byte in bd_addr_bytes)
    
    @staticmethod
    def bd_addr_str_to_bytes(bd_addr_str: str) -> bytes:
        """Convert BD_ADDR string to bytes"""
        if len(bd_addr_str) != 17 or bd_addr_str.count(':') != 5:
            raise ValueError("Invalid BD_ADDR format. Use XX:XX:XX:XX:XX:XX")
        try:
            return bytes.fromhex(bd_addr_str.replace(':', ''))
        except ValueError:
            raise ValueError("Invalid BD_ADDR format. Use XX:XX:XX:XX:XX:XX")
        
    @staticmethod
    def bd_addr_str_to_int(bd_addr_str: str) -> int:
        """Convert BD_ADDR string to integer"""
        return int(bd_addr_str.replace(':', ''), 16)
    
    @staticmethod
    def bd_addr_int_to_str(bd_addr_int: int) -> str:
        """Convert BD_ADDR integer to string"""
        if not (0 <= bd_addr_int < 0x1000000000000):
            raise ValueError("BD_ADDR integer must be in range 0 to 0xFFFFFFFFFFFF")
        return ':'.join(f'{(bd_addr_int >> (i * 8)) & 0xFF:02x}' for i in range(5, -1, -1))
    
    @staticmethod
    def bd_addr_bytes_to_int(bd_addr_bytes: bytes) -> int:
        """Convert BD_ADDR bytes to integer"""
        if len(bd_addr_bytes) != 6:
            raise ValueError("BD_ADDR must be 6 bytes long")
        return int.from_bytes(bd_addr_bytes, 'big')
    
    @staticmethod
    def bd_addr_int_to_bytes(bd_addr_int: int) -> bytes:
        """Convert BD_ADDR integer to bytes"""
        if not (0 <= bd_addr_int < 0x1000000000000):
            raise ValueError("BD_ADDR integer must be in range 0 to 0xFFFFFFFFFFFF")
        return bd_addr_int.to_bytes(6, 'big')
    
    @staticmethod
    def bd_addr_str_to_public(bd_addr_str: str) -> str:
        """Convert BD_ADDR string to public address format"""
        if not AddressUtil.is_random_address(bd_addr_str):
            raise ValueError("Address is not a random address")
        return '00:' + bd_addr_str[3:]  # Replace first two bytes with '00'
    
    @staticmethod
    def bd_addr_str_to_random(bd_addr_str: str) -> str:
        """Convert BD_ADDR string to random address format"""
        if not AddressUtil.is_public_address(bd_addr_str):
            raise ValueError("Address is not a public address")
        return '01:' + bd_addr_str[3:]  # Replace first two bytes with '01'
    
    @staticmethod
    def bd_addr_str_to_static(bd_addr_str: str) -> str:
        """Convert BD_ADDR string to static address format"""
        if not AddressUtil.is_random_address(bd_addr_str):
            raise ValueError("Address is not a random address")
        return '02:' + bd_addr_str[3:]  # Replace first two bytes with '02'
    
    @staticmethod
    def bd_addr_str_to_non_resolvable(bd_addr_str: str) -> str:
        """Convert BD_ADDR string to non-resolvable address format"""
        if not AddressUtil.is_random_address(bd_addr_str):
            raise ValueError("Address is not a random address")
        return '03:' + bd_addr_str[3:]  # Replace first two bytes with '03'
    
    @staticmethod
    def bd_addr_str_to_resolvable(bd_addr_str: str) -> str:
        """Convert BD_ADDR string to resolvable address format"""
        if not AddressUtil.is_random_address(bd_addr_str):
            raise ValueError("Address is not a random address")
        return '04:' + bd_addr_str[3:]  # Replace first two bytes with '04'
    
    @staticmethod
    def bd_addr_str_to_le_public(bd_addr_str: str) -> str:
        """Convert BD_ADDR string to LE public address format"""
        if not AddressUtil.is_random_address(bd_addr_str):
            raise ValueError("Address is not a random address")
        return '05:' + bd_addr_str[3:]  # Replace first two bytes with '05'
    
    @staticmethod
    def bd_addr_str_to_le_random(bd_addr_str: str) -> str:
        """Convert BD_ADDR string to LE random address format"""
        if not AddressUtil.is_public_address(bd_addr_str):
            raise ValueError("Address is not a public address")
        return '06:' + bd_addr_str[3:]  # Replace first two bytes with '06'
    
    @staticmethod
    def bd_addr_str_to_le_static(bd_addr_str: str) -> str:
        """Convert BD_ADDR string to LE static address format"""
        if not AddressUtil.is_random_address(bd_addr_str):
            raise ValueError("Address is not a random address")
        return '07:' + bd_addr_str[3:]  # Replace first two bytes with '07'
    
    @staticmethod
    def bd_addr_str_to_le_non_resolvable(bd_addr_str: str) -> str:
        """Convert BD_ADDR string to LE non-resolvable address format"""
        if not AddressUtil.is_random_address(bd_addr_str):
            raise ValueError("Address is not a random address")
        return '08:' + bd_addr_str[3:]  # Replace first two bytes with '08'
    
    @staticmethod
    def bd_addr_str_to_le_resolvable(bd_addr_str: str) -> str:
        """Convert BD_ADDR string to LE resolvable address format"""
        if not AddressUtil.is_random_address(bd_addr_str):
            raise ValueError("Address is not a random address")
        return '09:' + bd_addr_str[3:]  # Replace first two bytes with '09'
    

def generate_random_address() -> str:
    """Generate a random Bluetooth address"""
    return AddressUtil.generate_random_address()
def is_public_address(address: str) -> bool:
    """Check if the address is a public address"""
    return AddressUtil.is_public_address(address)
def is_random_address(address: str) -> bool:
    """Check if the address is a random address"""
    return AddressUtil.is_random_address(address)
def is_static_address(address: str) -> bool:
    """Check if the address is a static address"""
    return AddressUtil.is_static_address(address)
def bd_addr_bytes_to_str(bd_addr_bytes: bytes) -> str:
    """Convert BD_ADDR bytes to string"""
    return AddressUtil.bd_addr_bytes_to_str(bd_addr_bytes)
def bd_addr_str_to_bytes(bd_addr_str: str) -> bytes:
    """Convert BD_ADDR string to bytes"""
    return AddressUtil.bd_addr_str_to_bytes(bd_addr_str)
def bd_addr_str_to_int(bd_addr_str: str) -> int:
    """Convert BD_ADDR string to integer"""
    return AddressUtil.bd_addr_str_to_int(bd_addr_str)
def bd_addr_int_to_str(bd_addr_int: int) -> str:
    """Convert BD_ADDR integer to string"""
    return AddressUtil.bd_addr_int_to_str(bd_addr_int)
def bd_addr_bytes_to_int(bd_addr_bytes: bytes) -> int:
    """Convert BD_ADDR bytes to integer"""
    return AddressUtil.bd_addr_bytes_to_int(bd_addr_bytes)
def bd_addr_int_to_bytes(bd_addr_int: int) -> bytes:
    """Convert BD_ADDR integer to bytes"""
    return AddressUtil.bd_addr_int_to_bytes(bd_addr_int)
def bd_addr_str_to_public(bd_addr_str: str) -> str:
    """Convert BD_ADDR string to public address format"""
    return AddressUtil.bd_addr_str_to_public(bd_addr_str)
def bd_addr_str_to_random(bd_addr_str: str) -> str:
    """Convert BD_ADDR string to random address format"""
    return AddressUtil.bd_addr_str_to_random(bd_addr_str)
def bd_addr_str_to_static(bd_addr_str: str) -> str:
    """Convert BD_ADDR string to static address format"""
    return AddressUtil.bd_addr_str_to_static(bd_addr_str)
def bd_addr_str_to_non_resolvable(bd_addr_str: str) -> str:
    """Convert BD_ADDR string to non-resolvable address format"""
    return AddressUtil.bd_addr_str_to_non_resolvable(bd_addr_str)
def bd_addr_str_to_resolvable(bd_addr_str: str) -> str:
    """Convert BD_ADDR string to resolvable address format"""
    return AddressUtil.bd_addr_str_to_resolvable(bd_addr_str)
def bd_addr_str_to_le_public(bd_addr_str: str) -> str:
    """Convert BD_ADDR string to LE public address format"""
    return AddressUtil.bd_addr_str_to_le_public(bd_addr_str)
def bd_addr_str_to_le_random(bd_addr_str: str) -> str:
    """Convert BD_ADDR string to LE random address format"""
    return AddressUtil.bd_addr_str_to_le_random(bd_addr_str)
def bd_addr_str_to_le_static(bd_addr_str: str) -> str:
    """Convert BD_ADDR string to LE static address format"""
    return AddressUtil.bd_addr_str_to_le_static(bd_addr_str)
def bd_addr_str_to_le_non_resolvable(bd_addr_str: str) -> str:
    """Convert BD_ADDR string to LE non-resolvable address format"""
    return AddressUtil.bd_addr_str_to_le_non_resolvable(bd_addr_str)
def bd_addr_str_to_le_resolvable(bd_addr_str: str) -> str:
    """Convert BD_ADDR string to LE resolvable address format"""
    return AddressUtil.bd_addr_str_to_le_resolvable(bd_addr_str)    

# Export public functions   
__all__ = [
    'AddressUtil',
    'generate_random_address',
    'is_public_address',
    'is_random_address',
    'is_static_address',
    'bd_addr_bytes_to_str',
    'bd_addr_str_to_bytes',
    'bd_addr_str_to_int',
    'bd_addr_int_to_str',
    'bd_addr_bytes_to_int',
    'bd_addr_int_to_bytes',
    'bd_addr_str_to_public',
    'bd_addr_str_to_random',
    'bd_addr_str_to_static',
    'bd_addr_str_to_non_resolvable',
    'bd_addr_str_to_resolvable',
    'bd_addr_str_to_le_public',
    'bd_addr_str_to_le_random',
    'bd_addr_str_to_le_static',
    'bd_addr_str_to_le_non_resolvable',
    'bd_addr_str_to_le_resolvable'
]