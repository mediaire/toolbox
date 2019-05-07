import unittest
import logging
import tempfile
import time
import shutil
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

                # remove folders older than 1 day
                # and remove old folders as long as total size exceed 1 MB
                mock_cleaner = DataCleaner(temp_folder, 1024, 60 * 60 * 24)
                try:
                    removed = mock_cleaner.clean_up(dry_run=False)
                except:
                    self.fail("Early termination failed")
                self.assertTrue(len(removed) == 1)
                self.assertEqual(removed[0], sub_folder_3)
                shutil.rmtree(temp_folder)

    def test_filterlist(self):
        temp_folder = tempfile.mkdtemp(suffix='_test_5')
        _, tmp_file_1 = tempfile.mkstemp(suffix='.dcm', dir=temp_folder)
        _, tmp_file_2 = tempfile.mkstemp(suffix='.nifti', dir=temp_folder)

        filter_list = ['*.dcm']

        mock_cleaner = DataCleaner(temp_folder, -1, -1, filter_list=filter_list,
                                   white_list_mode=True)
        removed = mock_cleaner.clean_folder(temp_folder, dry_run=True) 
        self.assertTrue(len(removed) == 1)
        self.assertEqual(removed[0], tmp_file_2)

        mock_cleaner.white_list_mode = False
        removed = mock_cleaner.clean_folder(temp_folder, dry_run=True) 
        self.assertTrue(len(removed) == 1)
        self.assertEqual(removed[0], tmp_file_1)
        shutil.rmtree(temp_folder)
    
    def test_unix_filter(self):
        temp_folder = tempfile.mkdtemp(suffix='_test_6')
        _, tmp_file_1 = tempfile.mkstemp(prefix='Person1', suffix='.dcm', dir=temp_folder)
        _, tmp_file_2 = tempfile.mkstemp(prefix='Person2', suffix='.dcm', dir=temp_folder)
        
        filter_list = ['Person1*.dcm']

        mock_cleaner = DataCleaner(temp_folder, -1, -1, filter_list=filter_list,
                                   white_list_mode=True)
        removed = mock_cleaner.clean_folder(temp_folder, dry_run=True) 
        self.assertTrue(len(removed) == 1)
        self.assertEqual(removed[0], tmp_file_2)
        shutil.rmtree(temp_folder)