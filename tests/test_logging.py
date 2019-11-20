import unittest
from unittest.mock import patch
import logging
import io
from contextlib import redirect_stderr

from mediaire_toolbox.logging import base_logging_conf
from mediaire_toolbox.queue.tasks import Task


class TestLogging(unittest.TestCase):

    @unittest.skip
    # TODO
    def test_logging(self):
        f = io.StringIO()

        with redirect_stderr(f):
            base_logging_conf.basic_logging_conf()
            logger = logging.getLogger("test_logging")
            logger.info('Foo1')
            transaction_logger = base_logging_conf.logger_for_transaction("test_logging", 1)
            transaction_logger.info('Foo2')
            transaction_logger.info('Foo3')
            logger.info('Foo4')

        s = f.getvalue()
        lines = s.splitlines()
        print(lines)
        
        self.assertEqual(4, len(lines))
        for i in range(1, 4):
            self.assertTrue('Foo%s' % i in lines[i - 1])
        
        self.assertFalse('transaction=1' in lines[0])
        self.assertTrue('transaction=1' in lines[1])
        self.assertTrue('transaction=1' in lines[2])
        self.assertFalse('transaction=1' in lines[3])

    @patch('time.time')
    def test_log_runtime(self, mock_time):
        mock_time.return_value = 10

        @base_logging_conf.log_task_runtime
        def process_task(task):
            pass

        task = Task(t_id=1, tag='stage_1', data={})
        process_task(task)

        task.tag = 'stage_2'
        process_task(task)

        self.assertEqual(
            [('stage_1', 0), ('stage_2', 0)],
            task.data['runtime']
        )
