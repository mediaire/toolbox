import logging

def basic_logging_conf():
    logging.basicConfig(format='%(asctime)s %(levelname)s  %(module)s:%(lineno)s '
                               '%(message)s', level=logging.INFO)