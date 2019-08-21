import unittest
from copy import deepcopy

from mediaire_toolbox.queue.tasks import Task


class TestTask(unittest.TestCase):

    def setUp(self):
        self.task_d = {"t_id": 1,
                       "user_id": 10,
                       "tag": "spm_lesion",
                       "output": {"foo": "bar"},
                       "timestamp": 1530368396,
                       "data": {"dicom_info":
                                    {"t1": {"path": "path",
                                            "header": {"PatientName": "Max"}
                                            }
                                     }
                                }
                       }

    def test_read_dict(self):
        task = Task().read_dict(self.task_d)
        self.assertEqual(task.data['dicom_info']['t1']['path'], "path")

    def test_create_child(self):
        task = Task().read_dict(self.task_d)
        new_tag = 'child_task'
        child_task = task.create_child(new_tag)
        self.assertEqual(child_task.t_id, task.t_id)
        self.assertEqual(child_task.user_id, task.user_id)
        self.assertEqual(child_task.tag, new_tag)
        self.assertEqual(child_task.timestamp, task.timestamp)
        self.assertNotEqual(child_task.update_timestamp,
                            task.update_timestamp)
        self.assertGreaterEqual(child_task.update_timestamp,
                                task.timestamp)

    def test_child_does_not_influence_parent(self):
        task = Task().read_dict(self.task_d)
        new_tag = 'child_task'
        parent_task_data = deepcopy(task.data)
        child_task = task.create_child(new_tag)
        # change input of `child_task`
        child_task.data['out'] = 'bar'
        # this should not change output of parent task
        self.assertEqual(task.data, parent_task_data)

