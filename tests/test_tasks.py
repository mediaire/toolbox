import unittest
from copy import deepcopy

from mediaire_toolbox.queue.tasks import Task, DicomTask


DICOM_TASK = {'t1': 'info'}


class TestTask(unittest.TestCase):

    def setUp(self):
        self.task = Task(tag='tag',
                         input={'t1': 'foo', 't2': 'bar'},
                         output={'out': 'foo'})

    def test_to_dict(self):
        d = self.task.to_dict()
        self.assertIn('tag', d)
        self.assertIn('input', d)
        self.assertEqual(d['input']['t1'], 'foo')
        self.assertEqual(d['output']['out'], 'foo')
        self.assertEqual(d['tag'], 'tag')

    def test_from_and_to_bytes(self):
        bytes_ = self.task.to_bytes()
        task_from_bytes = Task().read_bytes(bytes_)
        self.assertEqual(task_from_bytes.__dict__ , self.task.__dict__)

    def test_create_child(self):
        new_tag = 'child_task'
        child_task = self.task.create_child(new_tag)
        self.assertEqual(child_task.tag, new_tag)
        self.assertEqual(child_task.timestamp, self.task.timestamp)
        self.assertNotEqual(child_task.update_timestamp,
                            self.task.update_timestamp)
        self.assertGreaterEqual(child_task.update_timestamp,
                            self.task.timestamp)

    def test_child_does_not_influence_parent(self):
        new_tag = 'child_task'
        parent_task_output = deepcopy(self.task.output)
        child_task = self.task.create_child(new_tag)
        # change input of `child_task`
        child_task.input['out'] = 'bar'
        # this should not change output of parent task
        self.assertEqual(self.task.output, parent_task_output)


class TestDicomTask(unittest.TestCase):

    def setUp(self):
        self.task = Task(tag='tag',
                         input={'t1': 'foo', 't2': 'bar'},
                         output={'out': 'foo'})
        self.dicom_task = DicomTask(tag='tag', input={'t1': 'foo', 't2': 'bar'},
                                    output={'out': 'foo'},
                                    dicom_info=DICOM_TASK)

    def test_dicom_info_has_correct_values(self):
        self.assertEqual(self.dicom_task.dicom_info, DICOM_TASK)
        self.assertEqual(self.dicom_task.data['dicom_info'], DICOM_TASK)

    def test_dicom_info_changes_correctly(self):
        self.dicom_task.data['dicom_info']['t3'] = 'foo'
        self.assertEqual(self.dicom_task.dicom_info['t3'],
                         self.dicom_task.data['dicom_info']['t3'] )
