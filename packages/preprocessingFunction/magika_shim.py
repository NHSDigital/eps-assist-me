"""
magika shim for markitdown when magika is not installed
returns failed status so markitdown falls back to file extension detection
"""


class Magika:
    def __init__(self, *args, **kwargs):
        pass

    def identify_stream(self, stream):
        return MagikaResult()


class MagikaResult:
    def __init__(self):
        self.status = "failed"


__version__ = "0.6.1"
__all__ = ["Magika"]
