<?php
$config = require __DIR__ . '/config.example.php';
$localConfig = __DIR__ . '/config.local.php';
return is_file($localConfig) ? array_merge($config, require $localConfig) : $config;