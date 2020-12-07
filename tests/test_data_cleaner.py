import unittest
import logging
import tempfile
import mock
import shutil
import time
import itertools
import os

from mediaire_toolbox.data_cleaner import DataCleaner

logging.basicConfig(format='%(asctime)s %(levelname)s  %(module)s:%(lineno)s '
                    '%(message)s', level=logging.DEBUG)


class TestDataCleaner(unittest.TestCase):
    """Test protected member functions"""
    def test_check_valid_init_raise(self):
        self.assertRaises(ValueError, DataCleaner, None, 1, 0, 0)

    def test_check_valid_init(self):
        DataCleaner(
            None, 0, 0, 0, -1,
            None, ['*.nii'], ['test.nii'])

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

    def test__remove_from_file_list_4(self):
        filelist = [0, 1, 2, 3, 4, 5, 6]
        DataCleaner._remove_from_file_list(filelist, [0, 0, 4, 2, 5, 1])
        self.assertEqual([3, 6], filelist)

    def test__fnmatch_1(self):
        self.assertFalse(DataCleaner._fnmatch('test.nii', []))

    def test__fnmatch_2(self):
        self.assertTrue(DataCleaner._fnmatch('test.nii', ['*.dcm', '*.nii']))

    def test__fnmatch_3(self):
        self.assertFalse(DataCleaner._fnmatch('test.nii', ['*.dcm']))

    def test__check_remove_filter(self):
        self.assertFalse(DataCleaner._check_remove_filter(
            'test.nii', [], []))

    def test__check_remove_filter2(self):
        self.assertFalse(
            DataCleaner._check_remove_filter('test.nii', ['*.dcm'], []))

    def test__check_remove_filter3(self):
        self.assertTrue(
            DataCleaner._check_remove_filter('test.nii', [], ['*.nii']))

    def test__check_remove_filter4(self):
        self.assertFalse(DataCleaner._check_remove_filter(
            'test.nii', None, None))

    def test__check_remove_filter5(self):
        """Both whitelist and blacklist"""
        self.assertFalse(DataCleaner._check_remove_filter(
            'test.nii', ['test.nii'], ['*.nii']))

    def test__check_remove_filter6(self):
        """Both whitelist and blacklist"""
        self.assertTrue(DataCleaner._check_remove_filter(
            'test.nii', ['not_test.nii'], ['*.nii']))

    """Test public functions"""

    def test_clean_file_folder(self):
        filelist = [
            ('folder1/file1.dcm', 0, 1),
            ('folder2/file2.dcm', 0, 3),
            ('folder1/file3.dcm', 0, 5),
            ('folder1/file4.nii', 0, 7),
            ('folder1/file5.dcm', 0, 9),
        ]
        removed, removed_index, removed_size = DataCleaner.clean_file_folder(
            filelist, 'folder1/file1.dcm', [], ['*.dcm']
        )

        self.assertEqual(
            [
                ('folder1/file3.dcm', 0, 5),
                ('folder1/file5.dcm', 0, 9),
            ], removed)

        self.assertEqual([2, 4], removed_index)
        self.assertEqual(14, removed_size)

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
                DataCleaner.clean_files_by_date(filelist, 6, [], ['*file*'])
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
                DataCleaner.clean_files_by_date(filelist, 6, ['file1'], ['*file*'])
            )
            self.assertEqual(
                [('file1', 0, 0),
                 ('file3', 5, 0),
                 ('file4', 7, 0)],
                filelist
            )

    def test_clean_files_by_size_1(self):
        self.assertEqual([], DataCleaner.clean_files_by_size_optimized(
            [], 1, [], []))

    def test_clean_files_by_size_2(self):
        filelist = [
            ('file1', 0, 10),
            ('file2', 0, 10),
            ('file3', 0, 10),
            ('file4', 0, 10)
        ]
        removed = DataCleaner.clean_files_by_size_optimized(
            filelist, 15, [], 'file*')
        self.assertEqual([('file1', 0, 10), ('file2', 0, 10)], removed)

    def test_clean_files_by_size_blacklist(self):
        filelist = [
            ('file1', 0, 10),
            ('file2', 0, 10),
            ('file3', 0, 10),
            ('file4', 0, 10)
        ]
        removed = DataCleaner.clean_files_by_size_optimized(
            filelist, 15, [], 'file3')
        self.assertEqual([('file3', 0, 10)], removed)

    def test_clean_files_by_size_whitelist(self):
        filelist = [
            ('file1', 0, 10),
            ('file2', 0, 10),
            ('file3', 0, 10),
            ('file4', 0, 10)
        ]
        removed = DataCleaner.clean_files_by_size_optimized(
            filelist, 15, ['file1'], 'file*')
        self.assertEqual([('file2', 0, 10), ('file3', 0, 10)], removed)

    def test_remove_files_file_nonexistent(self):
        fail_list = DataCleaner.remove_files(
            [('mockpath/that/does/not/exist', 0, 0)])
        self.assertEqual(['mockpath/that/does/not/exist'], fail_list)

    def test_remove_empty_folder_from_base_folder_1(self):
        try:
            base_folder = tempfile.mkdtemp()
            removed = DataCleaner.remove_empty_folder_from_base_folder(
                base_folder)
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

    def test_clean_up_priority_list(self):
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
            dc_instance = DataCleaner(
                folder='',
                folder_size_soft_limit=1.0*50/1024/1028,
                folder_size_hard_limit=1.0*50/1024/1028,
                max_data_seconds=10,
                whitelist=['file1', 'file3'],
                priority_list=['file2', 'file4', 'file*']
            )
            removed = dc_instance.clean_up(dry_run=True)
            # TODO file should be deleted only once
            self.assertEqual(
                [('file2', 5, 10),
                 ('file4', 13, 30),
                 ('file4', 13, 30)],
                removed
            )

    def test_clean_up_priority_list_2(self):
        with mock.patch.object(DataCleaner, 'scan_dir'), \
                mock.patch.object(DataCleaner, '_get_file_stats') as mock_files, \
                mock.patch.object(DataCleaner, '_get_current_time') as mock_time:
            # test that 1. files not in priority_list are not removed
            #    (t.db not removed)
            # 2. files removed are in the order of the priority list
            #    (old*.nii removed first)
            # 3. files on the whitelist are not removed
            #    (not removing file1.nii and file3.nii)
            # 4. stop the removing process early if size requirements met
            #    (0004.dcm not removed)
            mock_files.return_value = [
                ('folder1/0001.png', 0, 10),
                ('folder1/0002.png', 0, 10),
                ('folder1/0003.png', 0, 10),
                ('folder1/0004.png', 0, 10),
                ('folder1/folder2/file1.nii', 10, 30),
                ('folder1/folder2/old_file2.nii', 10, 30),
                ('folder1/folder2/old_file3.nii', 10, 30),
                ('folder1/folder2/file4.nii', 10, 30),
                ('folder2/t.db', 10, 40),

            ]
            mock_time.return_value = 20
            dc_instance = DataCleaner(
                folder='',
                folder_size_soft_limit=1.0*115/1024/1024,
                folder_size_hard_limit=1.0*115/1024/1024,
                max_data_seconds=-1,
                whitelist=['*file1.nii', '*file3.nii'],
                priority_list=['*old*.nii', '*nii', '*.png', 'file*']
            )
            removed = dc_instance.clean_up(dry_run=True)
            # TODO file should be ideally deleted only once
            self.assertEqual(
                [('folder1/folder2/old_file2.nii', 10, 30),
                 ('folder1/folder2/file4.nii', 10, 30),
                 ('folder1/folder2/old_file2.nii', 10, 30)],
                removed
            )

    def test_clean_up_priority_list_3_dcms(self):
        with mock.patch.object(DataCleaner, 'scan_dir'), \
                mock.patch.object(DataCleaner, '_get_file_stats') as mock_files, \
                mock.patch.object(DataCleaner, '_get_current_time') as mock_time:
            # test that 1. dcm files are removed on a whole
            mock_files.return_value = [
                ('folder1/0001.dcm', 0, 10),
                ('folder1/0002.dcm', 0, 10),
                ('folder1/0003.dcm', 0, 10),
                ('folder1/0004.dcm', 0, 10),
                ('folder2/0001.dcm', 10, 10),
                ('folder2/0002.dcm', 10, 10),
                ('folder2/folder3/file1.nii', 10, 10),
                ('folder3/0001.dcm', 5, 10),
                ('folder3/0002.dcm', 5, 10),
                ('folder3/t.db', 10, 10),

            ]
            mock_time.return_value = 20
            dc_instance = DataCleaner(
                folder='',
                folder_size_soft_limit=1.0*55/1024/1024,
                folder_size_hard_limit=1.0*55/1024/1024,
                max_data_seconds=-1,
                whitelist=[],
                priority_list=['*.dcm']
            )
            removed = dc_instance.clean_up(dry_run=True)
            self.assertEqual(
                [('folder1/0001.dcm', 0, 10),
                 ('folder1/0002.dcm', 0, 10),
                 ('folder1/0003.dcm', 0, 10),
                 ('folder1/0004.dcm', 0, 10),
                 ('folder3/0001.dcm', 5, 10),
                 ('folder3/0002.dcm', 5, 10)],
                removed
            )

    def test_do_not_clean_young_files(self):
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
            # file2 is 15 seconds old
            # file4 is 7 seconds old
            dc_instance = DataCleaner(
                folder='',
                folder_size_soft_limit=1024*1024,
                folder_size_hard_limit=1024*1024,
                max_data_seconds=10,
                whitelist=['file1', 'file3'],
                blacklist=['file*'],
                min_data_seconds=8
            )
            removed = dc_instance.clean_up(dry_run=True)
            self.assertEqual([('file2', 5, 10)], removed)

    def test_soft_hard_limit(self):
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
            dc_instance = DataCleaner(
                folder='',
                folder_size_soft_limit=1.0*40/1024/1028,
                folder_size_hard_limit=1.0*50/1024/1028,
                max_data_seconds=-1,
                whitelist=[''],
                priority_list=['file*']
            )
            removed = dc_instance.clean_up(dry_run=True)
            self.assertEqual(
                [('file2', 5, 10),
                 ('file3', 11, 30),
                 ('file4', 13, 30)],
                removed
            )

    def test_soft_hard_limit_2(self):
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
            dc_instance = DataCleaner(
                folder='',
                folder_size_soft_limit=1.0*40/1024/1028,
                folder_size_hard_limit=1.0*110/1024/1028,
                max_data_seconds=-1,
                whitelist=[''],
                priority_list=['file*']
            )
            removed = dc_instance.clean_up(dry_run=True)
            self.assertEqual([], removed)

    def test_scalability(self):
        # test that the function does not take too long
        list_of_folders = [str(i) for i in range(100)]

        dcm_files = ['{}.dcm'.format(i) for i in range(200)]

        filelist = [
            (os.path.join(a, b), 0, 1)
            for a, b in itertools.product(list_of_folders, dcm_files)]

        s_time = time.time()
        DataCleaner.clean_files_by_size_per_folder(
            filelist, reduce_size=100000000, pattern='*dcm')
        e_time = time.time()
        self.assertLess(e_time - s_time, 1.2)

    def test_scalability_2(self):
        # test that the function does not take too long
        list_of_folders = [str(i) for i in range(100)]

        dcm_files = ['{}.dcm'.format(i) for i in range(200)]

        filelist = [
            (os.path.join(a, b), 0, 1)
            for a, b in itertools.product(list_of_folders, dcm_files)]

        s_time = time.time()
        DataCleaner.clean_files_by_size_optimized(
            filelist, reduce_size=100000000, pattern='*dcm')
        e_time = time.time()
        self.assertLess(e_time - s_time, 1.2)
