import time
import json
from copy import deepcopy


class Task(object):
    """Defines task objects that can be handled by the task manager."""

    def __init__(self, tag=None, input=None, output=None, data=None,
                 timestamp=None, update_timestamp=None):
        """Initializes the Task object.

        Parameters
        ----------
        tag: str
            String specifying the task. Unique for each task.
        input: object
        output: object
        data: dict
        """
        self.tag = tag
        self.input = input
        self.output = output
        self.timestamp = timestamp or int(time.time())
        self.update_timestamp = update_timestamp
        self.data = data
        # self.update = None

    def to_dict(self):
        return {'tag': self.tag,
                'timestamp' : self.timestamp,
                'update_timestamp' : self.update_timestamp,
                'input': self.input,
                'output': self.output,
                'data': self.data}

    def to_bytes(self):
        return json.dumps(self.to_dict()).encode('utf-8')

    def read_dict(self, d):
        tag  = d['tag']
        timestamp  = d['timestamp']
        update_timestamp  = d.get('update_timestamp', None)
        input = d.get('input', None)
        output = d.get('output', None)
        data = d.get('data', None)
        self.__init__(tag, input, output, data, timestamp, update_timestamp)
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
        child_task = Task(tag=tag,
                          input=deepcopy(self.output), # be safe here
                          data=self.data, # this will never change
                          timestamp=self.timestamp,
                          update_timestamp=int(time.time())
                          )
        return child_task

    def __str__(self):
        return str(self.to_dict())

    def __repr__(self):
        return str(self.to_dict())


class DicomTask(Task):
    """Dicom specific task"""

    def get_subject_name(self):
        # the T1 header should always be there
        t1_header = self.data['dicom_info']['t1']['header']
        return t1_header['PatientName']

