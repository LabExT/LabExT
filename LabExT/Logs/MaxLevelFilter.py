
import logging
from logging import LogRecord

class MaxLevelFilter(logging.Filter):
    """
    This filter allows only the logging of messages up to a certain
    logging level.
    
    Attributes
    ----------
    max_level : int
        The highest logging level that is allowed
    """

    def __init__(self, max_level: int, name: str = "") -> None:
        """
        Initialize a filter that logs only messages with level less than 
        or equal to max_level.
        Initialize with the name of the logger which, together with its
        children, will have its events allowed through the filter. If no
        name is specified, allow every event.

        Parameters
        ----------
        max_level : int
            The highest logging level (included) to allow
        """
        super().__init__(name)
        self.max_level = max_level

    def filter(self, record: LogRecord) -> bool:
        return record.levelno <= self.max_level
