import os
import logging
import time

from mediaire_toolbox.queue.tasks import Task

"""
Provide a common interface for all our components to do logging
"""


def basic_logging_conf():
    """Will set up a basic logging configuration using basicConfig()"""
    return basic_logging_conf_with_level(
        logging.DEBUG if "MDBRAIN_DEBUG" in os.environ else logging.INFO)


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


def log_task_runtime(f):
    """Function decorator for logging and recording
    the runtime of a task in a component.
    NOTE function with side effects; the runtime is logged
    to the task.data dict
    NOTE this decorator should be decorating a plain
    process_task function, that takes an task object as the first
    arguement. The task object should be sent to the result queue after
    the call to the decorated function, thus
    this decorator is not meant to decorate
    the process_task method of QueueDaemon

    Usage:
    @log_task_runtime
    def process_task(task):
        ...
    """
    def wrapper(task: Task, *args, **kwargs):
        if not isinstance(task, Task):
            raise TypeError(
                "First arguement of the decorated"
                "function must be a task object!")

        start_time = time.time()
        result = f(task, *args, **kwargs)
        end_time = time.time()
        runtime = round(end_time - start_time, 4)

        logger_transaction = logger_for_transaction(
            'runtime_logger', task.t_id)
        logger_transaction.info(
            "Finished in {} seconds.".format(runtime))
        if task.data.get('runtime', []):
            task.data['runtime'].append([task.tag, runtime])
        else:
            task.data['runtime'] = [[task.tag, runtime]]
        return result
    return wrapper
