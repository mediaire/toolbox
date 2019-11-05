import json


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
