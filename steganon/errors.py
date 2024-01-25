class SteganonError(Exception):
    """Base Steganon exception"""

class StateAlreadyCreated(SteganonError):
    """Write/read state already created, can not use read/write"""

class SeedAlreadyUsed(SteganonError):
    """Old seed is already used, can not change it"""

class InvalidSeed(SteganonError):
    """Can not extract any data with specified seed"""

class TestModeEnabled(SteganonError):
    """TestMode was enabled. Can't use this feature."""
