import time
import json
from copy import deepcopy


class Task(object):
    """Defines task objects that can be handled by the task manager."""

    def __init__(self, tag=None, input=None, output=None, dicom_info=None,
                 timestamp=None, update_timestamp=None):
        """Initializes the Task object.

        Parameters
        ----------
        tag: str
            String specifying the task. Unique for each task.
        input
        output
        dicom_info: dict
            {'t1': {'header': {...}, 'path': 'path/to/dicoms',
             't2': {...}}
        """
        self.tag = tag
        self.input = input
        self.output = output
        self.timestamp = timestamp or int(time.time())
        self.update_timestamp = update_timestamp
        self.dicom_info = dicom_info
        # self.update = None

    def to_dict(self):
        return {'tag': self.tag,
                'timestamp' : self.timestamp,
                'update_timestamp' : self.update_timestamp,
                'input': self.input,
                'output': self.output,
                'dicom_info': self.dicom_info}

    def to_bytes(self):
        return json.dumps(self.to_dict()).encode('utf-8')

    def read_bytes(self, bytestring):
        d = json.loads(bytestring.decode('utf-8'))
        self.tag  = d['tag']
        self.timestamp  = d['timestamp']
        self.update_timestamp  = d.get('update_timestamp', None)
        self.input = d.get('input', None)
        self.output = d.get('output', None)
        self.dicom_info = d.get('dicom_info', None)
        return self

    def create_child(self, tag=None):
        """Creates and returns a follow up task object."""
        if tag is None:
            tag = self.tag + '__child'
        child_task = Task(tag=tag,
                          input=deepcopy(self.output), # be safe here
                          dicom_info=self.dicom_info, # this will never change
                          timestamp=self.timestamp,
                          update_timestamp=int(time.time())
                          )
        return child_task

    def __str__(self):
        return str(self.to_dict())

    def __repr__(self):
        return str(self.to_dict())