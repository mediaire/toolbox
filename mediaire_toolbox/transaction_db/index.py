import json
import logging

default_logger = logging.getLogger(__name__)


def index_institution(transaction):
    try:
        institution = (json.loads(transaction.last_message)['data']
                       ['dicom_info']['t1']['header']['InstitutionName'])
    except Exception:
        institution = ''
    transaction.institution = institution


def index_sequences(transaction):
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


def index_study_date(transaction):
    try:
        study_date = (json.loads(transaction.last_message)['data']
                      ['dicom_info']['t1']['header']['StudyDate'])
    except Exception:
        study_date = ''
    transaction.study_date = study_date


def index_version(transaction):
    try:
        version = (json.loads(transaction.last_message)['data']['version'])
    except Exception:
        version = None
    if version:
        transaction.version = version


def index_report_type(transaction):
    try:
        report_pdf_paths = (
            json.loads(transaction.last_message)['data']
            ['report_pdf_paths'])
    except Exception:
        report_pdf_paths = {}
    type_string = ';'.join(report_pdf_paths.keys())
    if type_string:
        transaction.report_type = type_string


def index_report_qa(transaction):
    try:
        report_qa_score_outcomes = (
            json.loads(transaction.last_message)['data']
            ['report_qa_score_outcomes'])
        default_logger.info(json.loads(transaction.last_message)['data'])
    except Exception:
        report_qa_score_outcomes = {}
    default_logger.info(report_qa_score_outcomes)
    qa_string = None
    if len(report_qa_score_outcomes.keys()) == 1:
        qa_string = report_qa_score_outcomes.values()[0]
    else:
        conc_strings = [
            "{}:{}".format(k, v) for k, v in report_qa_score_outcomes.items()]
        qa_string = ";".join(conc_strings)
    if qa_string:
        transaction.report_qa_score = qa_string
