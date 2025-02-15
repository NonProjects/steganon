class SteganonError(Exception):
    """Base Steganon exception"""
    def __init__(self, message: str=None):
        super().__init__(message or self.__doc__)

class StateAlreadyCreated(SteganonError):
    """Write/read state already created, can not use read/write"""

class SeedAlreadyUsed(SteganonError):
    """Old seed is already in use, can not change it"""

class InvalidSeed(SteganonError):
    """Can not extract any data with specified seed"""

class IncorrectDecode(SteganonError):
    """Can not extract any data due to error"""

class TestModeEnabled(SteganonError):
    """TestMode was enabled. Can't use this feature."""
