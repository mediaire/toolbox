import time
import json

from copy import deepcopy


class Task(object):
    """Defines task objects that can be handled by the task manager."""

    def __init__(self, t_id=None, user_id=None, product_id=None,
                 tag=None, data=None, coordinator_data=None,
                 timestamp=None, update_timestamp=None, error=None):
        """Initializes the Task object.

        Parameters
        ----------
        t_id: int
            transaction id this task belongs to
        user_id: int
            user_id who submitted this task, if applicable.
        product_id: int
            product_id of the product
        tag: str
            String specifying the task. Unique for each task.
        data: dict
            Data for specific products
        coordinator_data: dict
            Data for the coordinator module to use
        timestamp: float
            Timestamp of task creation from`time.time()`
        update_timestamp: float
            Timestamp of task update (via `create_child()`) from `time.time()`
        error: str
            a serialized error string in case the task failed while executing
        """
        self.t_id = t_id
        self.user_id = user_id
        self.product_id = product_id
        self.tag = tag
        self.timestamp = timestamp or int(time.time())
        self.update_timestamp = update_timestamp
        self.data = data
        self.coordinator_data = coordinator_data
        self.error = error
        # self.update = None

    def to_dict(self):
        return {'tag': self.tag,
                'timestamp': self.timestamp,
                'update_timestamp': self.update_timestamp,
                'data': self.data,
                'coordinator_data': self.coordinator_data,
                't_id': self.t_id,
                'user_id': self.user_id,
                'product_id': self.product_id,
                'error': self.error}

    def to_json(self):
        return json.dumps(self.to_dict())

    def to_bytes(self):
        return self.to_json().encode('utf-8')

    def read_dict(self, d):
        tag = d['tag']
        timestamp = d['timestamp']
        t_id = d.get('t_id', None)
        user_id = d.get('user_id', None)
        product_id = d.get('product_id', None)
        update_timestamp = d.get('update_timestamp', None)
        data = d.get('data', None)
        coordinator_data = d.get('coordinator_data', None)
        error = d.get('error', None)
        self.__init__(t_id=t_id, user_id=user_id,
                      product_id=product_id, tag=tag, data=data,
                      coordinator_data=coordinator_data,
                      timestamp=timestamp, update_timestamp=update_timestamp,
                      error=error)
        return self

    def read_bytes(self, bytestring):
        d = json.loads(bytestring.decode('utf-8'))
        self.read_dict(d)
        return self

    def read_json(self, json_path):
        with open(json_path, 'r') as f:
            d = json.load(f)
        self.read_dict(d)
        return self

    def create_child(self, tag=None):
        """Creates and returns a follow up task object."""
        if tag is None:
            tag = self.tag + '__child'
        child_task = deepcopy(self)
        child_task.tag = tag
        child_task.update_timestamp = int(time.time())
        return child_task

    def __str__(self):
        return str(self.to_dict())

    def __repr__(self):
        return self.__str__()


class CoordinatorData:
    schema_version: '1.0'

    @staticmethod
    def _update_process(
            task_progress=None, task_state=None,
            processing_state=None, source=None, dest=None):
        return {
            'transaction_db_update': {
                'task_progress': task_progress,
                'task_state': task_state,
                'processing_state': processing_state,
            },
            'source': 'source',
            'dest': 'dest',
            'schema_version': CoordinatorData.schema_version
        }

    @staticmethod
    def _send_to_pacs(version=None, source=None, dest=None):
        return {
            'send_to_pacs'
            'source': 'source',
            'dest': 'dest',
            'schema_version': CoordinatorData.schema_version
        }
