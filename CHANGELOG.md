# Changelog

## [0.14.0] - 2019-05-28
* DEV-412 Add skipped state to TransactionDB
* DEV-318 Task object refactor follow-up: delete input output field in tasks and delete DicomTask
* DEV-384 Optimize data cleaner

## [0.13.0] - 2019-04-18
* Fix DataCleaner - do nothing if -1 for both space and time

## [0.12.0] - 2019-04-10
* Auto-release script
* Bug in DataCleaner solved (folder size - int / str)

## [0.11.0] - 2019-01-21
* Move AssessmentEdit model classes from webinterface to here
* Provide universal way of logging in DEBUG mode

## [0.10.0] - 2019-01-15
* Bug in migration code, won't change schema version properly
* Cosmetic refactor (DEV-102)

## [0.9.0] - 2018-12-18
* New model for TransactionsDB with "task_progress" field.

## [0.8.0] - 2018-11-01
* TransactionsDB: a way of tracking cross-services 'transactions' in our system
* reusable logging primitives
* daemon base class

## [0.7.0] - 2018-10-15
* add linter
* data cleaner - cleans folders based on size and time

## [0.6.0] - 2018-07-02
* add error queue

## [0.5.1] - 2018-06-30
* fix create child task

## [0.5.0] - 2018-06-30
* redesign (strip down) dicom task

## [0.4.2] - 2018-06-30
* fix read_dict() no. 2

## [0.4.1] - 2018-06-30
* fix read_dict()

## [0.4.0] - 2018-06-30
* add dicom specific task

## [0.3.0] - 2018-06-08
* add read_dict, read_json

## [0.2.0] - 2018-05-30
* add travis ci
* add task object

## [0.1.0] - 2018-05-21
* add redis work queue prototype
