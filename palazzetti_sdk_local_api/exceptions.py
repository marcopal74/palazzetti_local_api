class LocalApiError(Exception):
    """Base class for other exceptions"""

    pass


class SendCommandError(LocalApiError):
    """Base class for other exceptions"""

    pass


class InvalidStateError(LocalApiError):
    """Base class for other exceptions"""

    pass


class InvalidStateTransitionError(LocalApiError):
    """Base class for other exceptions"""

    # pass


class NotAvailablePowerError(LocalApiError):
    """Base class for other exceptions"""

    pass


class InvalidLabelValueError(LocalApiError):
    """Base class for other exceptions"""

    pass


class InvalidFanError(LocalApiError):
    """Base class for other exceptions"""

    pass


class InvalidFanLimitsError(LocalApiError):
    """Base class for other exceptions"""

    pass


class InvalidFanOutOfRange(LocalApiError):
    """Base class for other exceptions"""

    pass


class InvalidFanMinMaxError(LocalApiError):
    """Base class for other exceptions"""

    pass


class InvalidDoorError(LocalApiError):
    """Base class for other exceptions"""

    pass


class InvalidLightError(LocalApiError):
    """Base class for other exceptions"""

    pass


class InvalidPowerError(LocalApiError):
    """Base class for other exceptions"""

    pass


class InvalidPowerMinMaxError(LocalApiError):
    """Base class for other exceptions"""

    pass


class NotAvailableSetpointError(LocalApiError):
    """Base class for other exceptions"""

    pass


class InvalidSetpointError(LocalApiError):
    """Base class for other exceptions"""

    pass


class InvalidSetpointMinMaxError(LocalApiError):
    """Base class for other exceptions"""

    pass