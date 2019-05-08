import subprocess
import time
import shutil
import os
import fnmatch
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

    def __init__(self, folder, max_folder_size, max_data_seconds,
                 whitelist=None, blacklist=None):
        """
        Parameters
        ----------
        whitelist: list
            Whitelist for files. Unix like filename pattern.
        blacklist: list
            Blacklist for files. Unix like filename pattern.
        """
        self.base_folder = folder
        self.max_folder_size = max_folder_size
        self.max_data_seconds = max_data_seconds
        self.whitelist = whitelist
        self.blacklist = blacklist
        if whitelist and blacklist:
            raise ValueError("Both black list and white list in instance")
        default_logger.info("""Instantiated a DataCleaner on folder {%s} with max 
                    foldersize={%s} and max data seconds={%s}""" %
                    (folder, max_folder_size, max_data_seconds))

    @staticmethod
    def current_size(folder):
        """disk usage in bytes"""
        return int(subprocess.check_output(['du', '-s', folder]) \
            .split()[0] \
            .decode('utf-8'))

    @staticmethod
    def creation_time(folder):
        return int(os.path.getmtime(folder))

    @staticmethod
    def list_sub_folders(folder):
        return [os.path.join(folder, sub_folder)
                for sub_folder in os.listdir(folder)]

    def clean_folder(self, folder, dry_run=False):
        """Cleans the folder given the filterlist.
        Can be either a blacklist or a whitelist.
        Deletes the files under the folder.
        """
        file_set = set([f for f in os.listdir(folder)
                        if os.path.isfile(os.path.join(folder, f))])
        if not file_set:
            if dry_run:
                default_logger.info('(dry-run) Would remove folder [%s]' % folder)
            else:
                default_logger.info('Removing folder [%s]' % folder)
                shutil.rmtree(folder)
            return None
    
        filter_set = set()
        filter_list = self.whitelist or self.blacklist
        for f in filter_list:
            filter_set = filter_set.union(set(fnmatch.filter(
                                          file_set, f)))

        if self.whitelist:
            delete_list = [os.path.join(folder, f) for f in 
                           list(file_set - filter_set)]
        else:
            delete_list = [os.path.join(folder, f) for f in 
                           list(filter_set)]

        for file_path in delete_list:
            if dry_run:
                default_logger.info('(dry-run) Would remove file [%s]' % file_path)
            else:
                default_logger.info('Removing file [%s]' % file_path)
                os.remove(file_path)
        return delete_list

    def clean_up(self, dry_run=False):
        """Cleans up, clean up folders that either take up too much space or 
        """
        removed = []
        if self.max_folder_size == -1 and self.max_data_seconds == -1:
            # nothing to be done
            return removed
        current_time = int(time.time())

        current_size = self.current_size(self.base_folder)

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

            if self.max_data_seconds > 0 and \
                                   (current_time - self.creation_time(folder)) > self.max_data_seconds:
                # base_folder is too old, must be deleted
                delete = True
                default_logger.info(
                    'Sub-folder is older than %s seconds, will delete' %
                    self.max_data_seconds)
            
            if  not delete:
                if self.max_folder_size > 0 \
                                    and current_size > self.max_folder_size:
                    # base_folder is still too big, let's delete this sub folder
                    delete = True
                    default_logger.info(
                        "Current total size is too big (%s bytes), \
                         need to delete some data to free up space" % current_size)
            if delete:
                removed.append(folder)
                pre_clean_size = self.current_size(folder)
                if dry_run:
                    default_logger.info('(dry-run) Would remove folder [%s]' % folder)
                    if self.whitelist or self.blacklist:
                        self.clean_folder(folder)
                else:
                    default_logger.info('Removing folder [%s]' % folder)
                    if self.whitelist or self.blacklist:
                        self.clean_folder(folder)
                        current_size = current_size - (pre_clean_size -
                                                   self.current_size(folder))
                    else:
                        shutil.rmtree(folder)
                        current_size = current_size - pre_clean_size

        return removed
