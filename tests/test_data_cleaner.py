import unittest
import logging
import tempfile
import time
import shutil
import os
import mock

from mediaire_toolbox.data_cleaner import DataCleaner

logging.basicConfig(format='%(asctime)s %(levelname)s  %(module)s:%(lineno)s '
                    '%(message)s', level=logging.DEBUG)


class TestUtils(unittest.TestCase):

    def test_remove_older_than_specified_age(self):
        # important, it's not atomic/thread-safe
        temp_folder = tempfile.mkdtemp(suffix='_test_1')
        sub_folder_1 = tempfile.mkdtemp(dir=temp_folder)
        sub_folder_2 = tempfile.mkdtemp(dir=temp_folder)

        current_time = time.time()

        def current_size(folder):
            folder_size = {temp_folder: 1024,
                           sub_folder_1: 512,
                           sub_folder_2: 512}
            return folder_size[folder]

        def creation_time(folder):
            # mock creation time so first folder is 10 seconds old and second
            # is 20 seconds old
            return int(current_time - 10) if folder == sub_folder_1 else int(current_time - 20)

        with mock.patch.object(DataCleaner, 'current_size') as mocked_current_size, \
             mock.patch.object(DataCleaner, 'creation_time') as mocked_creation_time:
                mocked_current_size.side_effect = current_size
                mocked_creation_time.side_effect = creation_time

                # remove folders older than 15 seconds
                mocked_data_cleaner = DataCleaner(temp_folder, 1024 * 1024, 15)

                removed = mocked_data_cleaner.clean_up(dry_run=True)
                self.assertTrue(len(removed) == 1)
                self.assertEqual(removed[0], sub_folder_2)
                shutil.rmtree(temp_folder)

    def test_remove_based_on_total_folder_size(self):
        temp_folder = tempfile.mkdtemp(suffix='_test_2')
        sub_folder_1 = tempfile.mkdtemp(dir=temp_folder)
        sub_folder_2 = tempfile.mkdtemp(dir=temp_folder)

        current_time = time.time()

        def current_size(folder):
            """mock current size so that it shrinks to 500 bytes if 
                one folder is deleted"""
            folder_size = {temp_folder: 1024*2,
                           sub_folder_1: 500,
                           sub_folder_2: 1024*2-500}
            return folder_size[folder]

        def creation_time(folder):
            return int(current_time - 10) if folder == sub_folder_1 else int(current_time - 20)

        with mock.patch.object(DataCleaner, 'current_size') as mocked_current_size, \
             mock.patch.object(DataCleaner, 'creation_time') as mocked_creation_time:
                mocked_current_size.side_effect = current_size
                mocked_creation_time.side_effect = creation_time

                # remove folders older than 1 day
                # and remove old folders as long as total size exceed 1 MB
                mock_cleaner = DataCleaner(temp_folder, 1024, 60 * 60 * 24)

                removed = mock_cleaner.clean_up(dry_run=False)
                self.assertTrue(len(removed) == 1)
                self.assertEqual(removed[0], sub_folder_2)
                shutil.rmtree(temp_folder)

    def test_dont_remove_if_negative_parameters(self):
        temp_folder = tempfile.mkdtemp(suffix='_test_3')
        _ = tempfile.mkdtemp(dir=temp_folder)
        _ = tempfile.mkdtemp(dir=temp_folder)
        # don't remove folders older than anything

        def current_size(folder):
            return 1024

        with mock.patch.object(DataCleaner, 'current_size') as mocked_current_size:
            mocked_current_size.side_effect = current_size
            mock_cleaner = DataCleaner(temp_folder, 1024 * 1024, -1)

            removed = mock_cleaner.clean_up(dry_run=True)
            self.assertTrue(removed == [])

            mock_cleaner = DataCleaner(temp_folder, -1, -1)

            removed = mock_cleaner.clean_up(dry_run=True)
            self.assertTrue(removed == [])

            shutil.rmtree(temp_folder)

    def test_early_termination(self):
        temp_folder = tempfile.mkdtemp(suffix='_test_4')
        sub_folder_1 = tempfile.mkdtemp(dir=temp_folder)
        sub_folder_2 = tempfile.mkdtemp(dir=temp_folder)
        sub_folder_3 = tempfile.mkdtemp(dir=temp_folder)

        current_time = time.time()

        def current_size(folder):
            # will raise a value error if sub_folder_1 is passed to the function
            try:
                folder_size = {temp_folder: 1024*2,
                               sub_folder_2: 200,
                               sub_folder_3: 1400}
                return folder_size[folder]
            except:
                raise ValueError("Early termination failed")

        def creation_time(folder):
            folder_time = {sub_folder_1: int(current_time - 10),
                           sub_folder_2: int(current_time - 20),
                           sub_folder_3: int(current_time - 30)}
            return folder_time[folder]

        with mock.patch.object(DataCleaner, 'current_size') as mocked_current_size, \
             mock.patch.object(DataCleaner, 'creation_time') as mocked_creation_time:
                mocked_current_size.side_effect = current_size
                mocked_creation_time.side_effect = creation_time

                # see if the clean_up function will query the size of sub_folder_1.
                # if the function calls current_size with sub_folder_1, an error is raised
                mock_cleaner = DataCleaner(temp_folder, 1024, -1)
                try:
                    removed = mock_cleaner.clean_up(dry_run=False)
                except:
                    self.fail("Early termination failed")
                self.assertTrue(len(removed) == 1)
                self.assertEqual(removed[0], sub_folder_3)
                shutil.rmtree(temp_folder)

    def test_both_whitelist_and_blacklist_instance(self):
        temp_folder = '/mock/path'
        filter_list = ['Person1*.dcm']
        with self.assertRaises(ValueError):
            DataCleaner(temp_folder, -1, -1, whitelist=filter_list,
                        blacklist=filter_list)
        
    def test_blacklist(self):
        temp_folder = tempfile.mkdtemp(suffix='_test_6')
        _, tmp_file_1 = tempfile.mkstemp(prefix='Person1', suffix='.dcm', dir=temp_folder)
        _, tmp_file_2 = tempfile.mkstemp(prefix='Person2', suffix='.dcm', dir=temp_folder)

        filter_list = ['Person1*.dcm']

        mock_cleaner = DataCleaner(temp_folder, -1, -1, blacklist=filter_list)
        removed = mock_cleaner.clean_folder(temp_folder, dry_run=True)
        self.assertTrue(len(removed) == 1)
        self.assertEqual(removed[0], tmp_file_1)
        shutil.rmtree(temp_folder)
    
    def test_whitelist(self):
        temp_folder = tempfile.mkdtemp(suffix='_test_7')
        _, tmp_file_1 = tempfile.mkstemp(prefix='Person1', suffix='.dcm', dir=temp_folder)
        _, tmp_file_2 = tempfile.mkstemp(prefix='Person2', suffix='.dcm', dir=temp_folder)

        filter_list = ['Person1*.dcm']

        mock_cleaner = DataCleaner(temp_folder, -1, -1, whitelist=filter_list)
        removed = mock_cleaner.clean_folder(temp_folder, dry_run=True)
        self.assertTrue(len(removed) == 1)
        self.assertEqual(removed[0], tmp_file_2)
        shutil.rmtree(temp_folder)

    def test_remove_empty_folder_with_whitelist(self):
        temp_folder = tempfile.mkdtemp(suffix='_test_8')
        _, tmp_file_1 = tempfile.mkstemp(prefix='Person1', suffix='.dcm', dir=temp_folder)

        filter_list = ['Person1*.dcm']

        mock_cleaner = DataCleaner(temp_folder, -1, -1, whitelist=filter_list)
        mock_cleaner.clean_folder(temp_folder, dry_run=False)
        self.assertTrue(os.path.isdir(temp_folder))
        shutil.rmtree(temp_folder)


    def test_partially_remove(self):
        """
        Test removing the correct folders when partially removing files using a filter.
        """
        temp_folder = tempfile.mkdtemp(suffix='_test_9')
        sub_folder_1 = tempfile.mkdtemp(dir=temp_folder)
        sub_folder_2 = tempfile.mkdtemp(dir=temp_folder)

        current_time = time.time()

        sub_folder_1_sizes = iter([500, 0, 0])
        sub_folder_2_sizes = iter([2048-500, 1100, 0])

        def current_size(folder):
            if folder == sub_folder_1:
                return next(sub_folder_1_sizes)
            if folder == sub_folder_2:
                return next(sub_folder_2_sizes)
            if folder == temp_folder:
                return 1024*2

        def creation_time(folder):
            folder_time = {sub_folder_1: int(current_time - 10),
                           sub_folder_2: int(current_time - 20)}
            return folder_time[folder]

        with mock.patch.object(DataCleaner, 'current_size') as mocked_current_size, \
             mock.patch.object(DataCleaner, 'creation_time') as mocked_creation_time, \
             mock.patch.object(DataCleaner, 'clean_folder') as mocked_clean_folder:
                mocked_current_size.side_effect = current_size
                mocked_creation_time.side_effect = creation_time
                mocked_clean_folder.side_effect = lambda x, y: None

                # remove with a max size of 1MB. 
                # If not using a filterlist, only sub_folder_2 will be deleted.
                # If using a filterlist as tested here, both folders will be cleaned. 
                mock_cleaner = DataCleaner(temp_folder, 1024, -1,
                                           whitelist=["mock"])
                removed = mock_cleaner.clean_up(dry_run=False)

                self.assertTrue(len(removed) == 2)
                self.assertEqual(removed[0], sub_folder_2)
                self.assertEqual(removed[1], sub_folder_1)
                shutil.rmtree(temp_folder)