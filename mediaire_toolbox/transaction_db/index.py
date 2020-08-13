import json
import logging

default_logger = logging.getLogger(__name__)


def set_index_institution(transaction):
    try:
        institution = (json.loads(transaction.last_message)['data']
                       ['dicom_info']['t1']['header']['InstitutionName'])
    except Exception:
        institution = ''
    transaction.institution = institution


def set_index_sequences(transaction):
    sequence_list = []
    for series_type in ['t1', 't2']:
        try:
            sequence = (json.loads(transaction.last_message)['data']
                        ['dicom_info'][series_type]['header']
                        ['SeriesDescription'])
            sequence_list.append(sequence)
        except Exception:
            pass
    transaction.sequences = ';'.join(sequence_list)


def set_index_study_date(transaction):
    try:
        study_date = (json.loads(transaction.last_message)['data']
                      ['dicom_info']['t1']['header']['StudyDate'])
    except Exception:
        study_date = ''
    transaction.study_date = study_date


def set_index_version(transaction):
    """Migration script. Index the version number in the last_message
    field to the 'version' column"""
    try:
        version = (json.loads(transaction.last_message)['data']['version'])
    except Exception:
        version = None
    if version:
        transaction.version = version


def set_index_analysis_type(transaction):
    """Migration script. Index the analysis type(s)
    of the transaction to the 'analysis type' column"""
    try:
        report_pdf_paths = (
            json.loads(transaction.last_message)['data']
            ['report_pdf_paths'])
        type_string = ';'.join(report_pdf_paths.keys())
    except Exception:
        if transaction.product_id == 2:
            type_string = 'mdspine_ms'
        else:
            type_string = 'mdbrain_nd'

    if type_string:
        transaction.analysis_type = type_string


def set_index_report_qa(transaction):
    """Migration script. Index the  qa score of the transaction
    to the 'qa_score' column"""
    try:
        qa_score_outcomes = (
            json.loads(transaction.last_message)['data']
            ['report_qa_score_outcomes'])
    except Exception:
        qa_score_outcomes = {}

    qa_string = None
    if len(qa_score_outcomes.keys()) == 1:
        qa_string = list(qa_score_outcomes.values())[0]
    else:
        conc_strings = [
            "{}:{}".format(k, v) for k, v in qa_score_outcomes.items()]
        qa_string = ";".join(conc_strings)
    if qa_string:
        transaction.qa_score = qa_string
