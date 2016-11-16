# Education Managements System

### Prepare
1. Prepare virtual environment: `virtualenv -p python2.7 venv`
2. Install requirements: `pip install -r requirements.txt`
3. Put OAuth2 credential file:  **clients.json** into `/cred/`

_Database server used in system is MySQL, configuate it in:_ `/config.py`

### Startup
Before startup regenerate database by command `db.create_all()` in `/app/__init__.py` file.