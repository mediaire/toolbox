import subprocess
import time
import shutil
import os
import logging


default_logger = logging.getLogger(__name__)

"""
Utility class for monitoring the disk usage in a folder and automatically 
cleaning up sub folders in case of need. Older sub folders would be cleaned up 
first.
You can also configure a number of seconds as age for sub folders, after which 
time it will be cleaned up. 
"""


class DataCleaner:

    def __init__(self, folder, max_folder_size, max_data_seconds):
        self.base_folder = folder
        self.max_folder_size = max_folder_size
        self.max_data_seconds = max_data_seconds
        default_logger.info("""Instantiated a DataCleaner on folder {%s} with max 
                    foldersize={%s} and max data seconds={%s}""" %
                    (folder, max_folder_size, max_data_seconds))

    def current_size(self):
        """disk usage in bytes"""
        return int(subprocess.check_output(['du', '-s', self.base_folder]) \
            .split()[0] \
            .decode('utf-8'))

    def creation_time(self, folder):
        return int(os.path.getmtime(folder))

    @staticmethod
    def list_sub_folders(folder):
        return [os.path.join(folder, sub_folder)
                for sub_folder in os.listdir(folder)]

    def clean_up(self, dry_run=False):
        removed = []
        if self.max_folder_size == -1 and self.max_data_seconds == -1:
            # nothing to be done
            return removed
        current_time = int(time.time())
        default_logger.debug('Current time is %s' % current_time)
        for folder in sorted(self.list_sub_folders(self.base_folder),
                             key=self.creation_time):
            # this already returns all sub-folders sorted from older to newer
            if not os.path.isdir(folder):
                # ignoring files by now
                continue
            default_logger.debug('Considering sub folder %s with creation time %s' % (
                folder, self.creation_time(folder)))
            delete = False

            if (self.max_data_seconds > 0 and 
               (current_time - self.creation_time(folder)) > self.max_data_seconds):
                # base_folder is too old, must be deleted
                delete = True
                default_logger.info(
                    'Sub-folder is older than %s seconds, will delete' %
                    self.max_data_seconds)

            current_size = self.current_size()

            if (not delete and self.max_folder_size > 0 
                and current_size > self.max_folder_size):
                # base_folder is still too big, let's delete this sub folder
                delete = True
                default_logger.info(
                    "Current total size is too big (%s bytes), need to delete some data to free up space" % current_size)
            if delete:
                removed.append(folder)
                if dry_run:
                    default_logger.info('(dry-run) Would remove folder [%s]' % folder)
                else:
                    default_logger.info('Removing folder [%s]' % folder)
                    shutil.rmtree(folder)
        return removed
