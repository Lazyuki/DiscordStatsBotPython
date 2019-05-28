# DiscordStatsBotPython
DiscordStatsBot (Ciri) migrated from Javascript to Python because why not.

## Setup
#### Get Python 3.6
1. `python3 -m venv ~/.venv/ciri`
1. `source ~/.venv/ciri/bin/activate`
1. `pip install -U -r requirements.txt`
####  Setup Postgres On GCP
1. `sudo apt-get update`
1. `sudo apt-get -y install postgresql postgresql-client postgresql-contrib`
1. `sudo -s`
1. `sudo -u postgres psql postgres`
1. `\password postgres` => enter password
1. `CREATE EXTENSION adminpack;`
1. `CREATE USER your_shell_name WITH PASSWORD '********';`
1. `\q`
1. `exit`
1. `psql postgres`
1. `CREATE DATABASE your_db_name`
1. `GRANT ALL PRIVILEGES ON DATABASE your_db_name TO your_shell_name;`
1. `\connect your_db_name`
1. `\i path_to_your_.sql_file`


