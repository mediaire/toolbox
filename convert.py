import logging
import json
import os

import SimpleITK as sitk

from md_commons.mdbrain.constants import MdbrainConstants
from md_commons.constants import MdsuiteConstants
from mediaire_toolbox.transaction_db.model import Transaction, TaskState
from mediaire_toolbox.logging import base_logging_conf
from suite_coordinator import utils

logger = logging.getLogger(__name__)


def nifti_file_conversion(path, output_path, logger):
    """Convert files to nifti

    Parameters
    ----------
    path: str
        input folder
    output_path: str
        output file name of the nifti file
    """
    logger.info("start file conversion folder '{}'".format(path))
    filenames = [f for f in os.listdir(path)
                 if os.path.isfile(os.path.join(path, f))]
    if not filenames:
        raise ValueError("No files in series path")

    if filenames[0].lower().endswith(('.dcm', '.ima', '.dps')):
        logger.info("file format is dicom")
        reader = sitk.ImageSeriesReader()
        dicom_names = reader.GetGDCMSeriesFileNames(path)
        reader.SetFileNames(dicom_names)
        image = reader.Execute()
        sitk.WriteImage(image, output_path)
    elif filenames[0].lower().endswith(('.nii', '.nii.gz', '.hdr')):
        logger.info("file format is nifti/hdr")
        reader = sitk.ImageFileReader()
        reader.SetImageIO("NiftiImageIO")
        reader.SetFileName(os.path.join(path, filenames[0]))
        image = reader.Execute()
        sitk.WriteImage(image, output_path)
    else:
        raise ValueError("No recognizable file ending of series found!")


def _convert_series_type(transaction, series_type):
    last_message = transaction.last_message

    if not last_message:
        logger.info(
            f"{transaction.transaction_id}: Last message does not exist!")
        return

    lm = json.loads(last_message)
    dest = os.path.join(
        lm.get('data', {}).get('spm_output_path'),
        MdbrainConstants.ORIG_T2_FILE_GZ)

    dicom_info = lm.get('data', {}).get('dicom_info')

    dicom_path = dicom_info.get(series_type, {}).get('path')

    if series_type in dicom_info and \
            os.path.isdir(dicom_path):
        if not os.path.exists(dest):
            nifti_file_conversion(dicom_path, dest, logger)
        else:
            logger.info(
                f"{transaction.transaction_id}: Orig file exists!")
    else:
        logger.info(
            f"{transaction.transaction_id}: No t2, skip!")


def convert(series_types=None):
    transaction_db = utils.get_transactions_db(MdsuiteConstants.DATA_DIR)

    base_query = transaction_db.session.query(Transaction)\
        .filter_by(task_state=TaskState.completed)\
        .filter_by(archived=0)

    for _type in series_types:
        transactions = [t for t in base_query]
        for t in transactions:
            try:
                _convert_series_type(t, _type)
            except Exception as e:
                logger.exception(e)
                logger.info(
                    f"{t.transaction_id}: Error in conversion")


if __name__ == "__main__":
    base_logging_conf.basic_logging_conf()
    convert(['t2'])
