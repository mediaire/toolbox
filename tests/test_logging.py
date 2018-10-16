import unittest
import logging
import io
from contextlib import redirect_stderr

from mediaire_toolbox.logging import base_logging_conf


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
