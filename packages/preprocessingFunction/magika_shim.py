"""
magika shim for markitdown when magika is not installed
returns failed status so markitdown falls back to file extension detection
"""


class Magika:
    def __init__(self, *args, **kwargs):
        """
        shim for Magika to prevent errors when it is not installed/needed
        """
        pass

    def identify_stream(self, stream):  # NOSONAR
        return MagikaResult()


class MagikaResult:
    def __init__(self):
        self.status = "failed"


__version__ = "0.6.1"
__all__ = ["Magika"]
