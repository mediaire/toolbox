# MEDIAIRE_TOOLBOX

Shared toolbox for our pipelines. 
* Logging conventions.
* Queue / Daemon classes.
* TransactionsDB (a generic way of persisting state through our pipelines).
* Data cleaner (a tool to periodically clean data on folders).

[![Build Status](https://travis-ci.org/mediaire/mediaire_toolbox.svg?branch=master)](https://travis-ci.org/mediaire/mediaire_toolbox)

Migration:
add an entry in migrate.py, and then change the version number in constants.py

DataCleaner:
`whitelist`, `blacklist` and `priority_list` are all glob patterns.
if in the `priority_list` is `*.dcm` or `*dcm` pattern, then when deciding to remove dcm
files, all files are removed from that folder for consistency.