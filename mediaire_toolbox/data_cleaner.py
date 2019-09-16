import time
import os
import fnmatch
import logging
import argparse

from mediaire_toolbox.logging.base_logging_conf import basic_logging_conf

default_logger = logging.getLogger(__name__)


class DataCleaner:
    """
    Utility class for monitoring the disk usage in a folder and automatically
    cleaning up files in case of need. Older files would be cleaned up
    first.
    You can also configure a number of seconds as age for files, after which
    time it will be cleaned up.

    There are several rules:
    1. Older files are checked first.
    2. For the size restriction, as long as time restriction
        is met, stop checking.
    3. whitelists/blacklists:
        a.) Files that match Whitelist patterns shall not be deleted, even if
        conditions not met
        b.) Files that do not match the Blacklist patterns shall not
        be deleted, even if conditions not met
    4. priority_lists function the same as the corresponding filter list.
        If the filterlist is a whitelist, then the priority list works
        as a whitelist extension.
    5. The priority of the priority_list is ascending:
        For a whitelist, if requirements not met, the items in the first
        list in the priority list are deleted, then the second ...
        For a blacklist, if requirements not met, the items in the last
        list in the priority list are deleted, then the second to last...
    """

    def __init__(self, folder, max_folder_size, max_data_seconds,
                 whitelist=None, blacklist=None, priority_list=None):
        """
        Parameters
        ----------
        folder:
            folder: str
            Path of folder to be cleaned.
        max_folder_size: int
            Max folder size (in MB), delete until current size is smaller than
            this.
            -1 if not deleting files based on size.
        max_data_seconds: int
            Max data age, delete folders that are older than this many seconds.
            -1 if not deleting files based on age.
        whitelist: list
            Whitelist for files. List of Unix like filename pattern strings.
        blacklist: list
            Blacklist for files. List of Unix like filename pattern strings.
        priority_list: list
            Priority list.
            List of files to keep/delete, importance from low to high.
            i.e if the priority_list = [[list_A], [list_B], [list_C]], and
            whitelist is used, then first the files outside the
            concatenation of the lists are deleted;
            if the data folder is still too large then files in list_A are
            deleted. Similarly, then the files in list_B and then at last
            files in list_C.
            NOTE: If whitelist and blacklist are both not given, the priority
            list will act like a whitelist
        """
        self.base_folder = folder
        self.max_folder_size = max_folder_size
        self.max_folder_size_bytes = 1.0 * max_folder_size * 1024 * 1024
        self.max_data_seconds = max_data_seconds
        self._check_filterlist_valid(whitelist, blacklist)
        self.whitelist = whitelist if whitelist else []
        self.blacklist = blacklist if blacklist else []
        default_logger.info(("Instantiated a DataCleaner on folder {%s} "
                            "with max foldersize={%s} and max data seconds={%s}")
                             %
                            (folder, max_folder_size, max_data_seconds))

        self.priority_list = priority_list if priority_list else []

    @staticmethod
    def _check_filterlist_valid(whitelist, blacklist):
        """Check if the filterlist is valid, raise error if
        whitelist and blacklist exist at the same time"""
        if whitelist and blacklist:
            raise ValueError("Both whitelist and blacklist in args")

    @staticmethod
    def scan_dir(path):
        """Scans the directory and its subfolders for all files,
        and return a list of filepaths"""
        entries = []
        for entry in os.scandir(path):
            # recursion when entry is a subfolder
            if entry.is_dir():
                entries += DataCleaner.scan_dir(os.path.join(path, entry.name))
            else:
                entries.append(os.path.join(path, entry.name))
        return entries

    @staticmethod
    def _creation_time_and_size(file):
        """Returns a (filename, creation_time, filesize) tuple"""
        stat = os.stat(file)
        return file, stat.st_ctime, stat.st_size

    @staticmethod
    def _get_file_stats(filelist):
        """Transforms a list of filenames to a list of
        (filename, creation_time, filesize) tuples"""
        return [DataCleaner._creation_time_and_size(f) for f in filelist]

    @staticmethod
    def _sort_filestat_list_by_time(filestat_list):
        """Sort the (filename, creation_time, filesize) list
        by time, ascending"""
        return sorted(filestat_list, key=lambda x: x[1])

    @staticmethod
    def _sum_filestat_list(filestat_list):
        """Get the total file size of a list of filestats"""
        return sum([size for _, _, size in filestat_list])

    @staticmethod
    def _get_current_time():
        return time.time()

    @staticmethod
    def _fnmatch(file, pattern_list):
        """Returns true if the filename matches with a list of patterns"""
        for pattern in pattern_list:
            if fnmatch.fnmatch(file, pattern):
                return True
        return False

    @staticmethod
    def _check_remove_time(c_time, max_data_seconds):
        """Returns true the file should be removed because it is too old"""
        age = DataCleaner._get_current_time() - c_time
        return max_data_seconds < age

    @staticmethod
    def _check_remove_filter(file, whitelist, blacklist):
        """Return true if file should be removed based on matched filename"""
        DataCleaner._check_filterlist_valid(whitelist, blacklist)
        if whitelist:
            return not DataCleaner._fnmatch(file, whitelist)
        if blacklist:
            return DataCleaner._fnmatch(file, blacklist)
        # no blacklist and whitelist, assume it can be removed
        return True

    @staticmethod
    def _remove_from_file_list(filelist, removed_index_list):
        """Remove the indexes of a inplace list given the
        list of indexes. NOTE function with side-effects"""
        shift_counter = 0
        for i in removed_index_list:
            del filelist[i-shift_counter]
            shift_counter += 1

    @staticmethod
    def _log_debug_removed(removed):
        """Show the files that are about to be removed"""
        default_logger.info("Removing files:")
        for file in removed:
            default_logger.info(
                "path:{}, creation_time:{}, size:{}"
                .format(file[0], file[1], file[2]))
        default_logger.info(
            "Total to be removed {} files, with the total size of {:.2f} MB"
            .format(len(removed),
                    DataCleaner._sum_filestat_list(removed)/1024/1024))

    @staticmethod
    def clean_files_by_date(filelist, max_data_seconds,
                            whitelist=None, blacklist=None):
        """Clean files that are older than max_data_seconds.

        Parameters
        ----------
        filelist: list
            list of remove candidates, sorted by time.
        max_data_seconds: int
            maximum allowed age for files.

        Returns
        -------
        list
            List of tuples. List of filestats the are to be removed"""
        removed = []
        removed_index_list = []
        for i in range(len(filelist)):
            file, creation_time, _ = filelist[i]
            if (DataCleaner._check_remove_filter(
                    file, whitelist, blacklist) and
                    DataCleaner._check_remove_time(
                    creation_time, max_data_seconds)):
                removed.append(filelist[i])
                removed_index_list.append(i)
        DataCleaner._remove_from_file_list(filelist, removed_index_list)
        return removed

    @staticmethod
    def clean_files_by_size(filelist, reduce_size,
                            whitelist=None, blacklist=None):
        """Clean the files by size.

        Parameters
        ----------
        filelist: list
            list of remove candidates, sorted by time
        reduce_size: int
            file size that needs to be removed to fulfill quota

        Returns
        -------
        list
            List of tuples. List of filestats the are to be removed
        """
        removed = []
        remove_size_counter = 0
        removed_index_list = []
        # do not clean if size requirements met
        if reduce_size < 0:
            return removed
        for i in range(len(filelist)):
            file, _, size = filelist[i]
            if DataCleaner._check_remove_filter(file, whitelist, blacklist):
                removed.append(filelist[i])
                removed_index_list.append(i)
                remove_size_counter += size
            if remove_size_counter > reduce_size:
                break
        DataCleaner._remove_from_file_list(filelist, removed_index_list)
        return removed

    @staticmethod
    def remove_files(remove_list):
        """Trie to remove the files from disk in the remove_list

        Returns
        -------
        list
            returns a list of to-be-removed files that failed.
        """
        fail_list = []
        for file, _, _ in remove_list:
            try:
                os.remove(file)
            except FileNotFoundError:
                fail_list.append(file)
            except Exception as e:
                default_logger.warn(
                    'Failed to remove file {}, with {}'
                    .format(file, str(e)))
                fail_list.append(file)
        return fail_list

    @staticmethod
    def remove_empty_folders(folder):
        """clean the base folder of empty directories"""
        removed = []
        for entry in os.scandir(folder):
            if entry.is_dir():
                removed += DataCleaner.remove_empty_folders(
                    os.path.join(folder, entry.name)
                )
        if not os.listdir(folder):
            os.rmdir(folder)
            return removed + [folder]
        return []

    @staticmethod
    def remove_empty_folder_from_base_folder(base_folder):
        """Parent function of remove_empty_folders so that the base folder
        is not deleted"""
        removed = []
        scan_dirs = [entry for entry in os.scandir(base_folder) if entry.is_dir()]
        for entry in scan_dirs:
            removed += DataCleaner.remove_empty_folders(
                os.path.join(base_folder, entry.name)
            )
        return removed

    def clean_up(self, dry_run=False,
                 whitelist=None, blacklist=None):
        """Clean up. The arguements whitelist and blacklist are for
        folders that should not/should be deleted on runtime, i.e folders that
        are being currently processed.

        Paremeters
        ----------
        dry_run: bool
            True if only returning the files to be deleted and not deleting them

        Return
        ------
        remove_list: list
            list of files to be removed
        """
        whitelist = whitelist + self.whitelist if whitelist else self.whitelist
        blacklist = blacklist + self.blacklist if blacklist else self.blacklist
        DataCleaner._check_filterlist_valid(whitelist, blacklist)
        filelist = self.scan_dir(self.base_folder)
        filelist = self._get_file_stats(filelist)
        filelist = self._sort_filestat_list_by_time(filelist)
        remove_list = []
        if self.max_data_seconds > 0:
            remove_list += self.clean_files_by_date(
                filelist, self.max_data_seconds, whitelist, blacklist
            )

        if self.max_folder_size_bytes > 0:
            current_size = self._sum_filestat_list(filelist)
            reduce_size = current_size - self.max_folder_size_bytes
            # NOTE if no blacklist or whitelist, prioritylist will act as whitelist
            # iter through the lists of priority_list

            # the priority_list is sorted by the priority, with the priority
            # ascending. Thus

            # if a priority_list is [[1], [2,3], [4]], and a whitelist is enabled
            # then add [1,2,3,4], [2,3,4] and [4] to each loop of the whitelist
            # Then files matching [1,2,3,4] are kept first,
            # and then files matching [2,3,4] etc

            # if a priority_list is [[1], [2,3], [4]], and a blacklist is enabled
            # then add [4], [2,3,4] and [1,2,3,4] to each loop of the blacklist
            # Then files matching [4] are deleted first, and then files matching
            # [2,3,4] etc
            for i in range(len(self.priority_list) + 1):
                if blacklist:
                    # get the blacklist with the priority_list added
                    priority_black_list = (
                        blacklist + self.priority_list[::-1][:i])
                    removed = self.clean_files_by_size(
                        filelist, reduce_size, blacklist=priority_black_list)
                else:
                    # get the whitelist with the priority_list added
                    priority_white_list = (
                        whitelist + self.priority_list[i:])
                    removed = self.clean_files_by_size(
                        filelist, reduce_size, whitelist=priority_white_list)
                reduce_size -= self._sum_filestat_list(removed)
                remove_list += removed
        if dry_run:
            self._log_debug_removed(remove_list)
        else:
            self.remove_files(remove_list)
            self.remove_empty_folder_from_base_folder(self.base_folder)
        return remove_list


def read_path(path):
    with open(path) as f:
        return [l.split()[0] for l in f.readlines()]


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
    parser.add_argument('--prioritylist', type=str, nargs='?',
                        help='prioritylist pathname')
    parser.add_argument('--dry_run', action="store_true", default=False)

    args = parser.parse_args()
    dry_run = args.dry_run

    basic_logging_conf()

    filter_path = args.blacklist or args.whitelist
    if filter_path:
        filter_list = read_path(filter_path)
    priority_path = args.prioritylist
    if priority_path:
        priority_list = read_path(priority_path)
    data_cleaner = DataCleaner(args.folder,
                               args.max_folder_size,
                               args.max_data_seconds,
                               whitelist=(filter_list
                                          if args.whitelist else None),
                               blacklist=(filter_list
                                          if args.blacklist else None),
                               priority_list=(priority_list
                                              if args.priority_path else None))
    data_cleaner.clean_up(dry_run=dry_run)


if __name__ == "__main__":
    main()
