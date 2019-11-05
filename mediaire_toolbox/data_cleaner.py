import subprocess
import time
import shutil
import os
import fnmatch
import logging
import argparse

from mediaire_toolbox.logging.base_logging_conf import basic_logging_conf

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
        folder:
            folder: str
            Path of folder to be cleaned.
        max_folder_size: int
            Max folder size (in KB), delete until current size is smaller than 
            this.
            -1 if not deleting files based on size.
        max_data_seconds: int
            Max data age, delete folders that are older than this many seconds.
            -1 if not deleting files based on age.
        whitelist: list
            Whitelist for files. List of Unix like filename pattern strings.
        blacklist: list
            Blacklist for files. List of Unix like filename pattern strings.
        """
        self.base_folder = folder
        self.max_folder_size = max_folder_size
        self.max_data_seconds = max_data_seconds
        self.whitelist = whitelist
        self.blacklist = blacklist
        if whitelist and blacklist:
            raise ValueError("Both black list and white list in instance")
        default_logger.info(("Instantiated a DataCleaner on folder {%s} "
                            "with max foldersize={%s} and max data seconds={%s}")
                             %
                            (folder, max_folder_size, max_data_seconds))

    @staticmethod
    def current_size(folder):
        """disk usage in bytes"""
        if os.path.isdir(folder):
            return int(subprocess.check_output(['du', '-s', folder])
                       .split()[0]
                       .decode('utf-8'))
        else:
            return 0

    @staticmethod
    def creation_time(folder):
        return int(os.path.getmtime(folder))

    @staticmethod
    def list_sub_folders(folder):
        return [os.path.join(folder, sub_folder)
                for sub_folder in os.listdir(folder)]

    def clean_folder(self, folder, dry_run=False):
        """Cleans the contents of the parameter folder.
        If the instance was configured with a whitelist or a blacklist,
        a selective delete will be performed accordingly."

        Returns
        -------
        list
            Returns the list of files deleted.
        """

        # get all folders and files in the folder
        file_list, folder_list = [], [folder]
        for root, directories, filenames in os.walk(folder, topdown=False):
            file_list += [os.path.join(root, filename)
                          for filename in filenames]
            folder_list += [os.path.join(root, directory)
                            for directory in directories]

        # the set of filtered files that match the whitelist/blacklist pattern
        filtered_files_set = set()
        # for every pattern in the whitelist/blacklist, match and join results
        for pattern in self.whitelist or self.blacklist:
            filtered_files_set = filtered_files_set.union(set(fnmatch.filter(
                                                          file_list, pattern)))

        if self.whitelist:
            # if it is a whitelist, the list of deleted files are the
            # files in the folder but not on the matched filenames
            delete_list = list(set(file_list) - filtered_files_set)
        else:
            # if it is a blacklist, the list of deleted files are
            # the files with matched filenames
            delete_list = list(filtered_files_set)

        for file_path in delete_list:
            if dry_run:
                default_logger.info('(dry-run) - '
                                    'Would remove file [%s]' % file_path)
            else:
                default_logger.info('Removing file [%s]' % file_path)
                os.remove(file_path)

        # remove the folder if it is empty after removing files
        if not dry_run:
            # start from the bottom
            for directory in folder_list[::-1]:
                if len(os.listdir(directory)) == 0:
                    default_logger.info('Removing '
                                        'empty folder [%s]' % directory)
                    os.rmdir(directory)
        return delete_list

    def clean_up(self, dry_run=False):
        """Cleans up folders that either take up too much space or are too old

        Returns
        -------
        list
            Returns the list of folders cleanded.
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
            default_logger.debug('Considering sub folder %s with creation time'
                                 '%s' % (folder, self.creation_time(folder)))
            delete = False

            if (self.max_data_seconds > 0 and
               (current_time - self.creation_time(folder)) >
               self.max_data_seconds):
                # base_folder is too old, must be deleted
                delete = True
                default_logger.info(
                    'Sub-folder is older than %s seconds, will delete' %
                    self.max_data_seconds)

            if (not delete and self.max_folder_size > 0
               and current_size > self.max_folder_size):
                # base_folder is still too big, let's delete this sub folder
                delete = True
                default_logger.info(
                    "Current total size is too big (%s bytes), need to "
                    "delete some data to free up space" % current_size)
            if delete:
                removed.append(folder)
                pre_clean_size = self.current_size(folder)
                # if whitelist/blacklist exists delete files from folder
                if self.whitelist or self.blacklist:
                    default_logger.info('Cleaning folder [%s]' % folder)
                    self.clean_folder(folder, dry_run)
                # if they don't exist delete the whole folder
                else:
                    if dry_run:
                        default_logger.info('(dry-run) - '
                                            'Would remove folder [%s]' % folder)
                    else:
                        default_logger.info('Removing folder [%s]' % folder)
                        shutil.rmtree(folder)

                # if the folder exists, the current size is subtracted with the
                # size of deleted files, which is the original sub folder size
                # minus the niew sub folder size
                current_size = current_size - (pre_clean_size -
                                               self.current_size(folder))

        return removed


def main():
    parser = argparse.ArgumentParser(
        description='clean folder')
    parser.add_argument('--folder', nargs='?', const=1, type=str,
                        help='root folder to be cleaned')
    parser.add_argument('--max_folder_size', nargs='?', const=1, type=int,
                        default=-1, help='maximum allowed folder size')
    parser.add_argument('--max_data_seconds', nargs='?', const=1, type=int,
                        default=-1, help='maximum allowed folder age')
    parser.add_argument('--whitelist', type=str, nargs='?',
                        help='whitelist pathname')
    parser.add_argument('--blacklist', type=str, nargs='?',
                        help='blacklist pathname')
    parser.add_argument('--dry_run', action="store_true", default=False)

    args = parser.parse_args()
    dry_run = args.dry_run
    
    basic_logging_conf()

    filter_path = args.blacklist or args.whitelist
    if filter_path:
        with open(filter_path) as f:
            filter_list = [l.split()[0] for l in f.readlines()]

    data_cleaner = DataCleaner(args.folder,
                               args.max_folder_size,
                               args.max_data_seconds,
                               whitelist=(filter_list
                                          if args.whitelist else None),
                               blacklist=(filter_list
                                          if args.blacklist else None))
    data_cleaner.clean_up(dry_run=dry_run)


if __name__ == "__main__":
    main()
