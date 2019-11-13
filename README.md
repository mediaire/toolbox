# MEDIAIRE_TOOLBOX

Shared toolbox for our pipelines. 
* Logging conventions.
* Queue / Daemon classes.
* TransactionsDB (a generic way of persisting state through our pipelines).
* Data cleaner (a tool to periodically clean data on folders).

[![Build Status](https://travis-ci.org/mediaire/mediaire_toolbox.svg?branch=master)](https://travis-ci.org/mediaire/mediaire_toolbox)

## DataCleaner

`whitelist`, `blacklist` and `priority_list` are all glob patterns.
If in the `priority_list` is `*.dcm` or `*dcm` pattern, then when deciding to remove dcm files, all files are removed from that folder for consistency.

## Migrations

Add an entry in migrate.py, and then change the version number in constants.py

## Running programmatic migrations manually

E.g. we want to run programmatic migration number 5 manually:

```
from mediaire_toolbox.transaction_db.transaction_db import migrate_scripts
from mediaire_toolbox.transaction_db.transaction_db import TransactionDB
from sqlalchemy import create_engine

engine = create_engine('sqlite:///t.db')
t_db = TransactionDB(engine)
migrate_scripts(t_db.session, engine, 4, 5)
```