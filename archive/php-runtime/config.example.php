<?php
return [
	'db_host' => getenv('MAPIDO_DB_HOST') ?: 'localhost',
	'db_port' => getenv('MAPIDO_DB_PORT') ?: '3306',
	'db_name' => getenv('MAPIDO_DB_NAME') ?: 'mapido',
	'db_user' => getenv('MAPIDO_DB_USER') ?: 'mapido_app',
	'db_pass' => getenv('MAPIDO_DB_PASS') ?: 'change-this-local-password',
];
