import unittest
import logging
import tempfile
import mock
import shutil

from mediaire_toolbox.data_cleaner import DataCleaner, main

logging.basicConfig(format='%(asctime)s %(levelname)s  %(module)s:%(lineno)s '
                    '%(message)s', level=logging.DEBUG)


class TestDataCleaner(unittest.TestCase):
    """Test protected member functions"""
    def test__creation_time_and_size(self):
        class mock_class():
            def __init__(self, time, size):
                self.st_ctime = time
                self.st_size = size
        with mock.patch('os.stat') as mock_stat:
            mock_stat.return_value = mock_class('time', 'size')
            self.assertEqual(
                ('file1', 'time', 'size'),
                DataCleaner._creation_time_and_size('file1')
            )

    def test__sum_filestat_list_1(self):
        self.assertEqual(0, DataCleaner._sum_filestat_list([]))

    def test__sum_filestat_list_2(self):
        self.assertEqual(
            1, DataCleaner._sum_filestat_list([("duh", 0, 1)]))

    def test__sum_filestat_list_3(self):
        self.assertEqual(
            3, DataCleaner._sum_filestat_list(
                [("duh", 0, 1), ("brah", 0, 2)]))

    def test__sort_filestat_list_1(self):
        self.assertEqual([], DataCleaner._sort_filestat_list_by_time([]))

    def test__sort_filestat_list_2(self):
        filelist = [('file1', 0, 0)]
        self.assertEqual(filelist, DataCleaner._sort_filestat_list_by_time(filelist))

    def test__sort_filestat_list_3(self):
        filelist = [('file1', 1, 0), ('file2', 0, 1)]
        self.assertEqual(
            filelist[::-1],
            DataCleaner._sort_filestat_list_by_time(filelist))

    def test__check_remove_time_True(self):
        with mock.patch.object(DataCleaner, '_get_current_time') as mock_time:
            mock_time.return_value = 2
            self.assertTrue(DataCleaner._check_remove_time(0, 1))

    def test__check_remove_time_False(self):
        with mock.patch.object(DataCleaner, '_get_current_time') as mock_time:
            mock_time.return_value = 1
            self.assertFalse(DataCleaner._check_remove_time(0, 1))

    def test__remove_from_file_list_1(self):
        filelist = []
        DataCleaner._remove_from_file_list(filelist, [])
        self.assertEqual([], filelist)

    def test__remove_from_file_list_2(self):
        filelist = [0]
        DataCleaner._remove_from_file_list(filelist, [0])
        self.assertEqual([], filelist)

    def test__remove_from_file_list_3(self):
        filelist = [0, 1, 2, 3]
        DataCleaner._remove_from_file_list(filelist, [0, 2])
        self.assertEqual([1, 3], filelist)

    def test__fnmatch_1(self):
        self.assertFalse(DataCleaner._fnmatch('test.nii', []))

    def test__fnmatch_2(self):
        self.assertTrue(DataCleaner._fnmatch('test.nii', ['*.dcm', '*.nii']))

    def test__fnmatch_3(self):
        self.assertFalse(DataCleaner._fnmatch('test.nii', ['*.dcm']))

    def test__check_remove_filter(self):
        self.assertTrue(DataCleaner._check_remove_filter(
            'test.nii', [], []))

    def test__check_remove_filter2(self):
        self.assertFalse(
            DataCleaner._check_remove_filter('test.nii', ['*.nii'], []))

    def test__check_remove_filter3(self):
        self.assertTrue(
            DataCleaner._check_remove_filter('test.nii', [], ['*.nii']))

    def test__check_remove_filter4(self):
        self.assertRaises(
            ValueError, DataCleaner._check_remove_filter,
            '', ['*.nii'], ['*.nii'])

    def test__check_remove_filter5(self):
        self.assertTrue(DataCleaner._check_remove_filter(
            'test.nii', None, None))

    def test__merge_lists_1(self):
        self.assertEqual([], DataCleaner._merge_lists([]))

    def test__merge_lists_2(self):
        self.assertEqual([0, 1], DataCleaner._merge_lists([[0], [1]]))

    def test__merge_lists_3(self):
        self.assertEqual(
            ['*.nii', '*.dcm'],
            DataCleaner._merge_lists([['*.nii'], ['*.dcm']]))

    def test__merge_lists_raise(self):
        self.assertRaises(
            ValueError,
            DataCleaner._merge_lists, [1, 2])

    """Test public functions"""

    def test_clean_files_by_date_1(self):
        self.assertEqual([], DataCleaner.clean_files_by_date([], 0, [], []))

    def test_clean_files_by_date_2(self):
        with mock.patch.object(DataCleaner, '_get_current_time') as mock_time:
            mock_time.return_value = 10
            filelist = [
                ('file1', 0, 0),
                ('file2', 3, 0),
                ('file3', 5, 0),
                ('file4', 7, 0)
            ]

            self.assertEqual(
                [('file1', 0, 0),
                 ('file2', 3, 0)],
                DataCleaner.clean_files_by_date(filelist, 6, [], [])
            )
            self.assertEqual(
                [('file3', 5, 0),
                 ('file4', 7, 0)],
                filelist
            )

    def test_clean_files_by_date_blacklist(self):
        with mock.patch.object(DataCleaner, '_get_current_time') as mock_time:
            mock_time.return_value = 10
            filelist = [
                ('file1', 0, 0),
                ('file2', 3, 0),
                ('file3', 5, 0),
                ('file4', 7, 0)
            ]

            self.assertEqual(
                [('file1', 0, 0)],
                DataCleaner.clean_files_by_date(filelist, 6, [], ['file1'])
            )
            self.assertEqual(
                [('file2', 3, 0),
                 ('file3', 5, 0),
                 ('file4', 7, 0)],
                filelist
            )

    def test_clean_files_by_date_whitelist(self):
        with mock.patch.object(DataCleaner, '_get_current_time') as mock_time:
            mock_time.return_value = 10
            filelist = [
                ('file1', 0, 0),
                ('file2', 3, 0),
                ('file3', 5, 0),
                ('file4', 7, 0)
            ]

            self.assertEqual(
                [('file2', 3, 0)],
                DataCleaner.clean_files_by_date(filelist, 6, ['file1'], [])
            )
            self.assertEqual(
                [('file1', 0, 0),
                 ('file3', 5, 0),
                 ('file4', 7, 0)],
                filelist
            )

    def test_clean_files_by_size_1(self):
        self.assertEqual([], DataCleaner.clean_files_by_size([], 1, [], []))

    def test_clean_files_by_size_2(self):
        filelist = [
            ('file1', 0, 10),
            ('file2', 0, 10),
            ('file3', 0, 10),
            ('file4', 0, 10)
        ]
        removed = DataCleaner.clean_files_by_size(filelist, 15, [], [])
        self.assertEqual([('file1', 0, 10), ('file2', 0, 10)], removed)
        self.assertEqual([('file3', 0, 10), ('file4', 0, 10)], filelist)

    def test_clean_files_by_size_blacklist(self):
        filelist = [
            ('file1', 0, 10),
            ('file2', 0, 10),
            ('file3', 0, 10),
            ('file4', 0, 10)
        ]
        removed = DataCleaner.clean_files_by_size(filelist, 15, [], ['file3'])
        self.assertEqual([('file3', 0, 10)], removed)
        self.assertEqual(
            [('file1', 0, 10),
             ('file2', 0, 10),
             ('file4', 0, 10)],
            filelist)

    def test_clean_files_by_size_whitelist(self):
        filelist = [
            ('file1', 0, 10),
            ('file2', 0, 10),
            ('file3', 0, 10),
            ('file4', 0, 10)
        ]
        removed = DataCleaner.clean_files_by_size(filelist, 15, ['file1'], [])
        self.assertEqual([('file2', 0, 10), ('file3', 0, 10)], removed)
        self.assertEqual([('file1', 0, 10), ('file4', 0, 10)], filelist)

    def test_remove_files_file_nonexistent(self):
        fail_list = DataCleaner.remove_files(
            [('mockpath/that/does/not/exist', 0, 0)])
        self.assertEqual(['mockpath/that/does/not/exist'], fail_list)

    def test_remove_empty_folder_from_base_folder_1(self):
        try:
            base_folder = tempfile.mkdtemp()
            removed = DataCleaner.remove_empty_folder_from_base_folder(base_folder)
            self.assertEqual([], removed)
        finally:
            shutil.rmtree(base_folder)

    def test_remove_empty_folder_from_base_folder_2(self):
        try:
            base_folder = tempfile.mkdtemp()
            tmp1 = tempfile.mkdtemp(dir=base_folder)
            tmp2 = tempfile.mkdtemp(dir=base_folder)
            tmp3 = tempfile.mkdtemp(dir=tmp1)
            tempfile.mkstemp(dir=tmp2)
            removed = DataCleaner.remove_empty_folder_from_base_folder(base_folder)
            self.assertEqual([tmp3, tmp1], removed)
        finally:
            shutil.rmtree(base_folder)

    def test_clean_up_priority_whitelist(self):
        with mock.patch.object(DataCleaner, 'scan_dir'), \
                mock.patch.object(DataCleaner, '_get_file_stats') as mock_files, \
                mock.patch.object(DataCleaner, '_get_current_time') as mock_time:
            mock_files.return_value = [
                ('file1', 15, 30),
                ('file2', 5, 10),
                ('file3', 11, 30),
                ('file4', 13, 30)
            ]
            mock_time.return_value = 20
            mock_priority = [['file1'], ['file3']]
            dc_instance = DataCleaner(
                folder='',
                max_folder_size=1.0*50/1024/1028,
                max_data_seconds=10,
                priority_list=mock_priority
            )
            removed = dc_instance.clean_up(dry_run=True)
            self.assertEqual(
                [('file2', 5, 10),
                 ('file4', 13, 30),
                 ('file1', 15, 30)],
                removed
            )
