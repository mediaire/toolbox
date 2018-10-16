import logging


"""
Provide a common interface for all our components to do logging
"""


def basic_logging_conf():
    """Will set up a basic logging configuration using basicConfig()"""
    return basic_logging_conf_with_level(logging.INFO)


def basic_logging_conf_with_level(level):
    logging.basicConfig(format='%(asctime)s %(levelname)s %(module)s:%(lineno)s '
                               '%(message)s', level=level)


def logger_for_transaction(name: str, t_id: int):
    """Provide a specific default_logger for a transaction. The provided transaction id
    will always be logged with every message.
    
    Parameters
    ----------
        name: str
            The default_logger ID
        t_id: int
            The transaction id
    """
    logger = logging.getLogger(name + "_" + str(t_id))

    class TransactionFilter(logging.Filter):
        def filter(self, record):
            record.transaction_id = t_id
            return True

    logger.addFilter(TransactionFilter())
    logger.propagate = False

    if len(logger.handlers) == 0:
        logger.addHandler(logging.StreamHandler())

    for handler in logger.handlers:
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s transaction=%(transaction_id)s '
            '%(module)s:%(lineno)s %(message)s'))

    return logger
