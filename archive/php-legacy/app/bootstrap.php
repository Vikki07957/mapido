<?php
declare(strict_types=1);

if (session_status() !== PHP_SESSION_ACTIVE) {
    $secure = !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off';
    ini_set('session.use_strict_mode', '1');
    ini_set('session.use_only_cookies', '1');
    ini_set('session.use_trans_sid', '0');
    session_set_cookie_params(['httponly' => true, 'secure' => $secure, 'samesite' => 'Lax']);
    session_start();
}

$config = require dirname(__DIR__) . '/config.php';
try {
    $pdo = new PDO(
        sprintf('mysql:host=%s;port=%s;dbname=%s;charset=utf8mb4', $config['db_host'], $config['db_port'], $config['db_name']),
        $config['db_user'],
        $config['db_pass'],
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC, PDO::ATTR_EMULATE_PREPARES => false]
    );
} catch (PDOException $exception) {
    http_response_code(503);
    exit('Database connection unavailable. Check config.php and import database/schema.sql.');
}

function e(mixed $value): string { return htmlspecialchars((string)$value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); }
function redirect(string $page): never { header('Location: index.php?page=' . rawurlencode($page)); exit; }
function csrf_token(): string { return $_SESSION['csrf'] ??= bin2hex(random_bytes(32)); }
function verify_csrf(): void {
    if (!hash_equals(csrf_token(), (string)($_POST['csrf'] ?? ''))) { http_response_code(419); exit('Your form expired. Please go back and try again.'); }
}
function current_user(): ?array { return $_SESSION['user'] ?? null; }
function require_login(): array {
    global $pdo;
    if (!current_user()) redirect('login');
    $statement=$pdo->prepare('SELECT role,is_suspended FROM users WHERE id=?'); $statement->execute([current_user()['id']]); $state=$statement->fetch();
    if (!$state || $state['is_suspended']) { $_SESSION=[]; session_regenerate_id(true); flash('This account is unavailable. Contact support for assistance.','danger'); redirect('login'); }
    $_SESSION['user']['role']=$state['role'];
    return current_user();
}
function require_admin(): array { $user = require_login(); if ($user['role'] !== 'admin') { http_response_code(403); exit('Administrator access required.'); } return $user; }
function flash(string $message, string $type = 'success'): void { $_SESSION['flash'] = ['message' => $message, 'type' => $type]; }
function notify(PDO $pdo, int $userId, string $message): void {
    $statement = $pdo->prepare('INSERT INTO notifications (user_id, message) VALUES (?, ?)');
    $statement->execute([$userId, $message]);
}
function valid_date(string $date): bool { $parsed = DateTime::createFromFormat('Y-m-d', $date); return $parsed && $parsed->format('Y-m-d') === $date; }