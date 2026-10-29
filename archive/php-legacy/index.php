<?php
declare(strict_types=1);
require __DIR__ . '/app/bootstrap.php';
require __DIR__ . '/app/actions.php';

$page = $_GET['page'] ?? 'home';
$allowed = ['home', 'login', 'register', 'dashboard', 'find', 'offer', 'bookings', 'chat', 'profile', 'support', 'admin'];
if (!in_array($page, $allowed, true)) { http_response_code(404); $page = 'home'; }
if (in_array($page, ['dashboard', 'offer', 'bookings', 'chat', 'profile'], true)) require_login();
if ($page === 'admin') require_admin();

$data = page_data($pdo, $page);
$flash = $_SESSION['flash'] ?? null;
unset($_SESSION['flash']);
?><!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#f5f8f3"><title><?= e($data['title'] ?? 'MAPIDO') ?> · MAPIDO</title>
  <link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="assets/style.css" rel="stylesheet">
</head>
<body>
<header class="site-header"><nav class="navbar navbar-expand-lg container py-3" aria-label="Main navigation">
  <a class="brand" href="index.php"><span class="brand-mark">M</span>MAPIDO</a>
  <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#mainNav" aria-label="Toggle navigation"><span class="navbar-toggler-icon"></span></button>
  <div class="collapse navbar-collapse" id="mainNav"><div class="navbar-nav ms-auto align-items-lg-center gap-lg-2">
    <a class="nav-link" href="index.php?page=find">Find a ride</a>
    <?php if (current_user()): ?>
      <a class="nav-link" href="index.php?page=dashboard">Dashboard</a><a class="nav-link" href="index.php?page=bookings">Bookings</a><a class="nav-link" href="index.php?page=chat">Messages</a><a class="nav-link" href="index.php?page=profile">Profile</a>
      <?php if (current_user()['role'] === 'admin'): ?><a class="nav-link" href="index.php?page=admin">Admin</a><?php endif; ?>
      <form method="post" action="index.php" class="d-inline"><input type="hidden" name="csrf" value="<?= e(csrf_token()) ?>"><input type="hidden" name="action" value="logout"><button class="btn btn-outline-dark btn-sm ms-lg-2">Log out</button></form>
    <?php else: ?><a class="nav-link" href="index.php?page=login">Log in</a><a class="btn btn-primary btn-sm ms-lg-2" href="index.php?page=register">Join MAPIDO <span aria-hidden="true">↗</span></a><?php endif; ?>
  </div></div>
</nav></header>
<main class="container page-shell">
  <?php if ($flash): ?><div class="alert alert-<?= e($flash['type']) ?> alert-dismissible fade show" role="status"><?= e($flash['message']) ?><button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button></div><?php endif; ?>
  <?php require __DIR__ . '/app/views/' . $page . '.php'; ?>
</main>
<footer class="site-footer"><div class="container d-flex flex-wrap justify-content-between gap-3"><span>MAPIDO <span class="footer-dot">·</span> Share the Ride, Split the Cost.</span><a href="index.php?page=support">Safety & support</a><span>Cost contributions are estimates agreed between riders.</span></div></footer>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script><script src="assets/app.js"></script>
</body></html>
