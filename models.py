# -*- coding: utf-8 -*-

import hashlib, json
from datetime import datetime

from flask import g
from flaskext.mysql import MySQL

cache = g.cache

def register_session(session_id, ipaddr, expire, userid, groups, loggedin):
	'''
	セッションのDB登録
	ユーザのアクティビティ更新
	'''
	db = g.db.get_db()
	db.cursor().execute('replace into sessions (id, ipaddr, userid, groups, loggedin, expire) values (%s, %s, %s, %s, %s, %s)',
		(session_id, ipaddr, userid if loggedin else None, json.dumps(groups) if loggedin else None, loggedin.isoformat() if loggedin else None, expire.isoformat()))
	db.commit()

def delete_session(session_id):
	'''
	セッションのDB削除
	ユーザのアクティビティ更新
	'''
	db = g.db.get_db()
	db.cursor().execute('delete from `sessions` where `id` = %s', session_id)
	db.commit()
	
def verify_session(session_id, ipaddr):
	'''
	セッションのDB検証
	接続IPアドレスとセッション期限を考慮し指定されたセッションIDが有効か判断
	'''
	db = g.db.get_db()
	c = db.cursor()
	c.execute('select ipaddr, userid, groups, loggedin from sessions where id = %s and expire >= now()', (session_id))
	record = c.fetchone()
	if not record:
		return (False, None)
	if record[0] != ipaddr:
		delete_session(db, session_id)
		return (False, None)
	return (True, record[1], json.loads(record[2]) if record[2] else None, record[3])

def verify_user(email, password):
	'''
	メールアドレスとパスワードからユーザログイン可否検証
	'''
	password_hash = hashlib.sha256(password).hexdigest()
	db = g.db.get_db()
	c = db.cursor()
	c.execute('select u.id from users u left join users_password p on p.id = u.id where email = %s and password = %s', (email, password_hash))
	record = c.fetchone()
	if record:
		# 認証OK
		userid = record[0];
		groups = []
		c = db.cursor()
		c.execute('select groupid from users_groups where userid = %s', (userid))
		record = c.fetchone()
		while record:
			groups.append(record[0])
			record = c.fetchone()
		return (True, userid, groups)
	else:
		# 認証NG
		return (False, None, None)

@cache.memoize()
def get_file_list(id):
	'''
	指定したディレクトリ内のディレクトリとファイルを取得
	'''
	list = []
	db = g.db.get_db()
	c = db.cursor()
	if id:
		condition = 'parent = %s'
		args = (id, id)
	else:
		condition = 'parent is null'
		args = None
	c.execute('(select 0 as type, id, owner, `group`, permission, name, NULL as filepath, datatype, extra from directories where ' + condition + ' order by name) ' +
		'union all (select 1 as type, id, owner, `group`, permission, name, filepath, datatype, extra from files where ' + condition + ' order by name)', args)
	record = c.fetchone()
	while record:
		list.append({
			'isdir'	: (record[0] == 0),
			'id'	: record[1],
			'owner'	: record[2],
			'group'	: record[3],
			'perm'	: record[4],
			'name'	: record[5],
			'dtype'	: record[7],
			'extra'	: record[8]})
		record = c.fetchone()
	return list

def directory_create(parent, owner, group, permission, name, datatype, extra):
	db = g.db.get_db()
	c = db.cursor()
	c.execute('insert into directories (parent, owner, `group`, permission, name, datatype, extra) values (%s, %s, %s, %s, %s, %s, %s)', 
		(parent, owner, group, permission, name, datatype, extra)) 
	db.commit()
	cache.delete_memoized(get_file_list, parent)
	cache.delete_memoized(directory_get_level, parent)
	return c.lastrowid;

def directory_delete(id, parent):
	db = g.db.get_db()
	c = db.cursor()
	c.execute('delete from directories where id = %s', (id))
	db.commit()
	cache.delete_memoized(get_file_list, parent)
	cache.delete_memoized(directory_get_by_id, id)
	cache.delete_memoized(directory_get_level, id)
	return id
	
@cache.memoize()
def directory_get_by_id(id):
	if not id:
		return ({
		'id'	: None,
		'parent': None,
		'owner'	: None,
		'group'	: None,
		'perm'	: 0x755,
		'name'	: None,
		'dtype'	: None,
		'extra'	: None})
	db = g.db.get_db()
	c = db.cursor()
	c.execute('select id, parent, owner, `group`, permission, name, datatype, extra from directories where id = %s', (id))
	record = c.fetchone()
	if not record:
		return None
	return ({
		'id'	: record[0],
		'parent': record[1],
		'owner'	: record[2],
		'group'	: record[3],
		'perm'	: record[4],
		'name'	: record[5],
		'dtype'	: record[6],
		'extra'	: record[7]})

@cache.memoize()
def directory_get_level(id):
	db = g.db.get_db()
	c = db.cursor()
	c.execute('CALL `get_directory_level`(%s)', id);
	record = c.fetchone()
	retval = []
	while record:
		retval.append(record[1])
		record = c.fetchone()
	return retval

def exists_by_name(parent, name):
	if parent:
		condition = 'parent = %s'
		args = (parent, name, parent, name)
	else:
		condition = 'parent is null'
		args = (name, name)
	db = g.db.get_db()
	c = db.cursor()
	c.execute('(select id from directories where ' + condition +' and name = %s) union all (select id from files where ' + condition + ' and name = %s)', args)
	return (c.fetchone() != None)

@cache.memoize()
def file_get_by_id(id):
	if not id:
		return None
	db = g.db.get_db()
	c = db.cursor()
	c.execute('select id, parent, owner, `group`, permission, name, filepath, datatype, extra from files where id = %s', (id))
	record = c.fetchone()
	if not record:
		return None
	return ({
		'id'	: record[0],
		'parent': record[1],
		'owner'	: record[2],
		'group'	: record[3],
		'perm'	: record[4],
		'name'	: record[5],
		'path'	: record[6],
		'dtype'	: record[7],
		'extra'	: record[8]})

def file_create(parent, owner, group, permission, name, datatype, extra, filepath):
	if not parent:
		return None
	db = g.db.get_db()
	c = db.cursor()
	c.execute('insert into files (parent, owner, `group`, permission, name, filepath, datatype, extra) values (%s, %s, %s, %s, %s, %s, %s, %s)',
		(parent, owner, group, permission, name, filepath, datatype, extra))
	db.commit()
	cache.delete_memoized(get_file_list, parent)
	return c.lastrowid;

def file_delete(id, parent):
	if not parent:
		return id
	db = g.db.get_db()
	c = db.cursor()
	c.execute('delete from files where id = %s', (id))
	db.commit()
	cache.delete_memoized(file_get_by_id, id)
	cache.delete_memoized(get_file_list, parent)
	return id