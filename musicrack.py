# -*- coding: utf-8 -*-

import uuid
import datetime
from flask import Flask, render_template, session, request, g
from flaskext.mysql import MySQL
from flask.ext.cache import Cache

from views.session import session as v_session
from views.files import files as v_files

DEBUG = True

app = Flask(__name__)
# Configure
app.config['STORAGE_PATH'] = 'D:\\MusicRack\\store'
app.config['ALLOWED_EXTENSIONS'] = ('mp3', 'png', 'mp4')

app.config['JSONIFY_PRETTYPRINT_REGULAR'] = DEBUG
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
app.config['MYSQL_DATABASE_PORT'] = 3306
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = None
app.config['MYSQL_DATABASE_DB'] = 'musicrack'
app.config['MYSQL_DATABASE_CHARSET'] = 'utf8'
app.config['SESSION_TIMEOUT'] = datetime.timedelta(7)
app.config['CACHE_CONFIG'] = {
	'CACHE_TYPE': 'simple',
	'CACHE_DEFAULT_TIMEOUT': 600
}
app.config['SECRET_KEY'] = 'rT4EgGRZ4uSrjPeU_ND9FwAdLD7EtAZw'

# DB Initialize
db = MySQL()
db.init_app(app)

# Cache Initialize
cache = Cache(config=app.config['CACHE_CONFIG'])
cache.init_app(app)

# Register session API
app.register_blueprint(v_session, url_prefix='/session')
# Register directory API
app.register_blueprint(v_files, url_prefix='/files')

@app.route('/')
def index():
	return render_template('/index.html')
	
@app.route('/test')
def test():
	return render_template('test/index.html')

@app.route('/initdb')
def initdb():
	with app.open_resource('schema.sql', mode='r') as f:
		script = f.read()
		g.db.get_db().cursor().executemany(script, None)
	return script

# Session handling
@app.before_request
def before_request():
	# Session ID
	g.db = db
	g.cache = cache
	
	import models
	g.models = models
	
	if 'sessionid' in request.cookies:
		# Session ID exists
		session_id = request.cookies['sessionid']
		(verified, userid, groups, loggedin) = models.verify_session(session_id, request.remote_addr)
		if not verified:
			session_id = str(uuid.uuid4())
		else:
			g.user_id = userid
			g.groups = groups
			g.loggedin = loggedin
	else:
		# Not exists
		session_id = str(uuid.uuid4())
	g.session_id = session_id

@app.after_request
def after_request(response):
	response.set_cookie('sessionid', value=g.session_id, max_age=app.config['SESSION_TIMEOUT'])
	g.models.register_session(g.session_id, 
		request.remote_addr, 
		datetime.datetime.now() + app.config['SESSION_TIMEOUT'],
		g.user_id, g.groups, g.loggedin)
	
	return response

if __name__ == '__main__':
    app.run(debug=True)
