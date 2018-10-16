import logging
import traceback
import os

from abc import ABC, abstractmethod
from sqlalchemy import create_engine

from mediaire_toolbox.queue.redis_wq import RedisWQ
from mediaire_toolbox.queue import tasks
from mediaire_toolbox.transaction_db.transaction_db import TransactionDB

logger = logging.getLogger(__name__)


class QueueDaemon(ABC):

    def __init__(self,
                 input_queue: RedisWQ,
                 result_queue: RedisWQ,
                 lease_secs: int,
                 daemon_name: str,
                 config: dict):
        self.input_queue = input_queue
        self.result_queue = result_queue
        self.lease_secs = lease_secs
        self.daemon_name = daemon_name
        self.config = config
        self.stopped = False
        # =====================================================================
        # TODO Change engine, SQLITE can't be an option from multiple processes
        # =====================================================================
        uri = "sqlite:///" + os.path.join(config['data_dir'], 't.db') + \
            '?check_same_thread=False'
        logger.info('Creating SQL connection for TransactionDB on %s' % uri)
        engine = create_engine(uri)
        self.transaction_db = TransactionDB(engine)

    @abstractmethod
    def process_task(self, task):
        pass

    def run_once(self):
        logger.info('Waiting for items from queue {}'.format(
            self.input_queue._main_q_key))
        item = self.input_queue.lease(
            lease_secs=self.lease_secs, block=True)
        try:
            task = tasks.Task().read_bytes(item)
            try:
                self.process_task(task)
                self.input_queue.complete(item)
            except Exception as e:
                logger.exception(
                    "Error processing task in %s" % self.daemon_name)
                tb = traceback.format_exc()
                msg = "{} --> in '{}': {}".format(e, __file__, tb)
                if task.t_id:
                    self.transaction_db.set_failed(task.t_id, msg)
                self.input_queue.error(item, msg=msg)
        except Exception as e:
            logger.exception("Operating error or error deserializing task object")
            tb = traceback.format_exc()
            self.input_queue.error(item, 
                                   msg="""{} --> in '{}': {}""".format(e, __file__, tb))

    def run(self):
        while not self.stopped:
            self.run_once()

    def stop(self):
        self.stopped = True
