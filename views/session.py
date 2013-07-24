# -*- coding: utf-8 -*-

import datetime
from flask import Blueprint, request, g, jsonify, current_app 


session = Blueprint('session', __name__)

@session.route('/isloggedin', methods=['GET'])
def isloggedin():
	return jsonify({'success': True, 'isloggedin': (g.loggedin != None)})
	
@session.route('/login', methods=['POST'])
def login():
	'''
	session/login API
	'''
	email = request.json['email']
	password = request.json['password']
	(verified, userid, groups) = g.models.verify_user(email, password)
	if verified:	
		g.user_id = userid
		g.groups = groups
		g.loggedin = datetime.datetime.now()
	else:
		g.user_id = None
		g.user_id = None
		g.loggedin = None
	return jsonify({'success': verified, 'userid': g.user_id, 'groups': g.groups})

@session.route('/logout', methods=['POST'])
def logout():
	'''
	session/logout API
	'''
	if g.loggedin == None:
		return jsonify({'success': False, 'reason': 'not_loggedin'})
	else:
		g.user_id = None
		g.loggedin = None
		return jsonify({'success': True})