USE `musicrack`;
drop table if exists `users`;
create table `users` (
	`id` integer unsigned primary key auto_increment,
	`name` varchar(30) not null,
	`email` varchar(256) not null,
	`isadmin` boolean not null default FALSE,
	`created` datetime not null,
	`modified` datetime not null,
	`disabled` boolean not null default FALSE
) engine=InnoDB;
drop table if exists `users_password`;
create table `users_password` (
	`id` integer unsigned primary key,
	`password` varchar(64),
	`modified` datetime not null
) engine=InnoDB;
drop table if exists `users_activity`;
create table `users_activity` (
	`id` integer unsigned primary key,
	`last_loggedin` datetime,
	`last_request` datetime
) engine=InnoDB;

drop table if exists `groups`;
create table `groups` (
	`id` integer unsigned primary key auto_increment,
	`name` varchar(30) not null,
	`isdefault` boolean not null default FALSE
) engine=InnoDB;
insert into `groups` (`name`) values ('root');
insert into `groups` (`name`, `isdefault`) values ('users', TRUE);
drop table if exists `users_groups`;
create table `users_groups` (
	userid integer unsigned not null,
	groupid integer unsigned  not null,
	primary key (userid, groupid)
) engine=InnoDB;

drop table if exists `sessions`;
create table `sessions` (
	`id` varchar(36) primary key,
	`ipaddr` varchar(16) not null,
	`userid` integer unsigned,
	`groups` varchar(50),
	`loggedin` datetime,
	`expire` datetime
) engine=InnoDB;

drop table if exists `directories`;
create table `directories` (
	`id` bigint unsigned primary key auto_increment,
	`parent` bigint unsigned,
	`owner` integer unsigned not null,
	`group` integer unsigned not null,
	`permission` smallint unsigned not null default '493',
	`name` varchar(255) not null,
	`datatype` integer unsigned,
	`extra` text
 ) engine=InnoDB;
create index `directories_parent_idx` on directories (parent);
insert into `directories` (`owner`, `group`, `permission`, `name`) values (1, 1, 493, 'root');

drop table if exists `files`;
create table `files` (
	`id` bigint unsigned primary key auto_increment,
	`parent` bigint unsigned,
	`owner` integer unsigned not null,
	`group` integer unsigned not null,
	`permission` smallint(3) unsigned not null default '420',
	`name` varchar(255) not null,
	`filepath` varchar(1023) not null,
	`datatype` integer unsigned,
	`extra` text
 ) engine=InnoDB;
create index `files_parent_idx` on files (parent);

CREATE DEFINER=`root`@`localhost` PROCEDURE `get_directory_level`(IN `p_id` INT)
	LANGUAGE SQL
	NOT DETERMINISTIC
	CONTAINS SQL
	SQL SECURITY DEFINER
	COMMENT ''
BEGIN
	DECLARE v_parent, v_lastid INT unsigned;
	
	create temporary table tree_level (
		`count` integer primary key auto_increment,
		`id` integer unsigned
	) engine=memory;
	
	SET v_lastid = p_id;
	test: LOOP
		b_loop: BEGIN
			DECLARE cur CURSOR FOR select parent from directories where id = v_lastid;
			OPEN cur;
			FETCH cur INTO v_parent;
			insert into tree_level(id) values (v_lastid);
			IF v_parent is null THEN LEAVE test; END IF;
			SET v_lastid = v_parent;
		END b_loop;
	END LOOP test;
	
	select * from tree_level;
	drop temporary table tree_level;
END