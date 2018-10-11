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

        def current_size():
            return 1024

        def creation_time(folder):
            """mock creation time so first folder is 10 seconds old and second is 20 seconds old"""
            return int(current_time - 10) if folder == sub_folder_1 else int(current_time - 20)

        with mock.patch.object(DataCleaner, 'current_size') as mocked_current_size:
            mocked_current_size.side_effect = current_size
            with mock.patch.object(DataCleaner, 'creation_time') as mocked_creation_time:
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

        def current_size():
            """mock current size so that it shrinks to 500 bytes if 
                one folder is deleted"""
            if len(DataCleaner.list_sub_folders(temp_folder)) > 1:
                return 1024 * 2
            else:
                return 500

        def creation_time(folder):
            return int(current_time - 10) if folder == sub_folder_1 else int(current_time - 20)

        with mock.patch.object(DataCleaner, 'current_size') as mocked_current_size:
            mocked_current_size.side_effect = current_size
            with mock.patch.object(DataCleaner, 'creation_time') as mocked_creation_time:
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

        def current_size():
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
