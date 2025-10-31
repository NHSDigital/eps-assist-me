"""Service-level exceptions for the slackBotFunction."""


class ConfigurationError(Exception):
    """Raised when there's a configuration issue"""

    pass


class PromptNotFoundError(Exception):
    """Raised when a prompt cannot be found by name"""

    pass


class PromptLoadError(Exception):
    """Raised when a prompt fails to load"""

    pass
