# -*- coding: utf-8 -*-

import datetime, os
from flask import Blueprint, request, g, jsonify, current_app

files = Blueprint('files', __name__)

@files.route('/list/', methods=['GET'])
def list_root():
	'''
	files/list API (for Root Directory)
	'''
	return list(None)

@files.route('/list/<int:id>', methods=['GET'])
def list(id):
	'''
	files/list API
	'''
	models = g.models;
	id = int(id) if id else None
	if not g.loggedin:
		return jsonify({'success': False, 'reason': 'not_loggedin'})
	
	dirinfo = models.directory_get_by_id(id)
	if dirinfo:
		if can_exec(dirinfo['perm'], dirinfo['owner'], dirinfo['group']):
			return jsonify({'success': True, 'list': models.get_file_list(id)})
		else:
			return jsonify({'success': False, 'reason': 'permission_denied'})
	else:
		return jsonify({'success': False, 'reason': 'not_found'})

@files.route('/directory/create', methods=['POST'])
def create_directory():
	'''
	files/directory/create API
	'''
	models = g.models;
	if not g.loggedin:
		return jsonify({'success': False, 'reason': 'not_loggedin'})
	
	parent = request.json['parent']
	if parent == None or parent == '':
		return jsonify({'success': False, 'reason': 'parent_required'})
	parent = int(parent)
	owner = g.user_id
	group = g.groups[0]
	permission = 0o755
	name = request.json['name']
	if name == None or name == '':
		return jsonify({'success': False, 'reason': 'name_required'})
	datatype = None
	extra = None
	reason = None
	
	dirinfo = models.directory_get_by_id(parent)
	if dirinfo:
		if can_write(dirinfo['perm'], dirinfo['owner'], dirinfo['group']):
			if not models.exists_by_name(parent, name):
				# 同一名ファイルが存在しない
				return jsonify({'success': True, 'list': models.directory_create(parent, owner, group, permission, name, datatype, extra)})
			else:
				reason = 'name_duplicated'
		else:
			reason = 'permission_denied'
	else:
		# parentが見つからない
		reason = 'parent_not_found'
	return jsonify({'success': False, 'reason': reason})

@files.route('/directory/delete', methods=['POST'])
def delete_directory():
	'''
	files/directory/delete API
	'''
	models = g.models;
	if not g.loggedin:
		return jsonify({'success': False, 'reason': 'not_loggedin'})
	
	id = request.json['id']
	if id == None or id == '':
		return jsonify({'success': False, 'reason': 'id_required'})
	id = int(id)
	reason = None
	
	dirinfo = models.directory_get_by_id(id)
	if dirinfo and dirinfo['parent']:
		if can_exec(dirinfo['perm'], dirinfo['owner'], dirinfo['group']):
			models.directory_delete(id, dirinfo['parent'])
			return jsonify({'success': True, 'id': id})
		else:
			reason = 'permission_denied'
	else:
		# parentが見つからない
		reason = 'parent_not_found'
	return jsonify({'success': False, 'reason': reason})

@files.route('/file/upload', methods=['POST'])
def upload_file():
	'''
	files/file/upload API
	'''
	models = g.models;
	if not g.loggedin:
		return jsonify({'success': False, 'reason': 'not_loggedin'})
	
	file = request.files['file']
	filename = file.filename
	parent = request.form['parent']
	if parent == None or parent == '':
		return jsonify({'success': False, 'reason': 'parent_required'})
	parent = int(parent)
	reason = None
	dirinfo = models.directory_get_by_id(parent)
	if dirinfo:
		if can_write(dirinfo['perm'], dirinfo['owner'], dirinfo['group']):
			if file and allowed_file(filename):
				if not models.exists_by_name(parent, filename):
					dirpath = os.path.join(current_app.config['STORAGE_PATH'], os.sep.join([str(x) for x in models.directory_get_level(parent)]))
					filepath = save_file(file, dirpath, filename)
					extradata = read_extra(filepath)
					fileid = models.file_create(parent, g.user_id, g.groups[0], 0o644, filename, None, None, filepath)
					return jsonify({'success': True, 'id': fileid})
				else:
					reason = 'name_duplicated'
			else:
				reason = 'filetype_not_allowed'
		else:
			reason = 'permission_denied'
	else:
		reason = 'parent_not_found'
	return jsonify({'success': False, 'reason': reason})

def save_file(filedata, dirpath, filename):
	'''
	ファイル保存
	'''
	filepath = os.path.join(dirpath, filename)
	if not os.path.exists(dirpath):
		os.makedirs(dirpath)
	filedata.save(filepath)
	return filepath

def read_extra(filepath):
	'''
	追加情報
	'''
	return None

def allowed_file(filename):
	'''
	拡張子判断
	'''
	return '.' in filename and filename.rsplit('.', 1)[1] in current_app.config['ALLOWED_EXTENSIONS']

@files.route('/file/delete', methods=['POST'])
def delete_file():
	models = g.models;
	if not g.loggedin:
		return jsonify({'success': False, 'reason': 'not_loggedin'})
	
	id = request.json['id']
	if id == None or id == '':
		return jsonify({'success': False, 'reason': 'id_required'})
	id = int(id)
	reason = None
	
	fileinfo = models.file_get_by_id(id)
	if not fileinfo:
		return jsonify({'success': False, 'reason': 'file_not_found'})
	if not can_write(fileinfo['perm'], fileinfo['owner'], fileinfo['group']):
		return jsonify({'success': False, 'reason': 'permission_denied'})
	
	models.file_delete(id, fileinfo['parent'])
	os.remove(os.path.join(current_app.config['STORAGE_PATH'], fileinfo['path']))
	return jsonify({'success': True, 'id': id})

def can_exec(permission, owner, group):
	'''
	実行権限評価
	'''
	isowner = g.user_id == owner
	if isowner:
		return (permission & 0o444 != 0)
	isgroup = group in g.groups
	if isgroup:
		return (permission & 0o044 != 0)
	return (permission & 0o004 != 0)

def can_write(permission, owner, groups):
	'''
	書込権限評価
	'''
	isowner = g.user_id == owner
	if isowner:
		return (permission & 0o222 != 0)
	isgroup = group in g.groups
	if isgroup:
		return (permission & 0o022 != 0)
	return (permission & 0o002 != 0)
	
def can_read(permission, owner, groups):
	'''
	読込権限評価
	'''
	isowner = g.user_id == owner
	if isowner:
		return (permission & 0o111 != 0)
	isgroup = group in g.groups
	if isgroup:
		return (permission & 0o011 != 0)
	return (permission & 0o001 != 0)