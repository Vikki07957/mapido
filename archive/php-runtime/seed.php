<?php
declare(strict_types=1);

if (PHP_SAPI !== 'cli') { http_response_code(404); exit; }
$config=require __DIR__.'/config.php';
$pdo=new PDO(sprintf('mysql:host=%s;port=%s;dbname=%s;charset=utf8mb4',$config['db_host'],$config['db_port'],$config['db_name']),$config['db_user'],$config['db_pass'],[PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION,PDO::ATTR_DEFAULT_FETCH_MODE=>PDO::FETCH_ASSOC]);
$accounts=[
 ['MAPIDO Demo Driver','driver@mapido.local','DriverDemo!2026','driver'],
 ['MAPIDO Demo Passenger','passenger@mapido.local','RiderDemo!2026','passenger'],
 ['MAPIDO Demo Admin','admin@mapido.local','AdminDemo!2026','admin'],
];
$pdo->beginTransaction();
try {
 $userStmt=$pdo->prepare('INSERT INTO users (name,email,password_hash,role) VALUES (?,?,?,?) ON DUPLICATE KEY UPDATE name=VALUES(name),password_hash=VALUES(password_hash),role=VALUES(role),is_suspended=0');
 $ids=[];
 foreach($accounts as [$name,$email,$password,$role]){$userStmt->execute([$name,$email,password_hash($password,PASSWORD_DEFAULT),$role]);$find=$pdo->prepare('SELECT id FROM users WHERE email=?');$find->execute([$email]);$ids[$role]=(int)$find->fetchColumn();}
 $vehicleStmt=$pdo->prepare('INSERT INTO vehicles (user_id,model,registration_number) VALUES (?,?,?) ON DUPLICATE KEY UPDATE model=VALUES(model),registration_number=VALUES(registration_number)');$vehicleStmt->execute([$ids['driver'],'Demo hatchback','KA 19 DZ 2046']);$vehicle=$pdo->prepare('SELECT id FROM vehicles WHERE user_id=?');$vehicle->execute([$ids['driver']]);$vehicleId=(int)$vehicle->fetchColumn();
 $routes=[['Sullia','Mangaluru',1,'08:15:00',600],['Mangaluru','Puttur',3,'09:00:00',400],['Puttur','Bengaluru',7,'21:30:00',1800]];
 $findRide=$pdo->prepare('SELECT id FROM rides WHERE driver_id=? AND origin=? AND destination=? AND is_sample=1');$addRide=$pdo->prepare('INSERT INTO rides (driver_id,vehicle_id,origin,destination,travel_date,departure_time,total_seats,estimated_cost,notes,is_sample) VALUES (?,?,?,?,?,?,3,?,?,1)');$refresh=$pdo->prepare('UPDATE rides SET vehicle_id=?,travel_date=?,departure_time=?,total_seats=3,estimated_cost=?,notes=? WHERE id=?');
 foreach($routes as [$origin,$destination,$offset,$time,$cost]){$date=(new DateTimeImmutable('today'))->modify('+'.$offset.' days')->format('Y-m-d');$findRide->execute([$ids['driver'],$origin,$destination]);$existing=$findRide->fetchColumn();if($existing){$refresh->execute([$vehicleId,$date,$time,$cost,'Demonstration route. Sample data only.',$existing]);}else{$addRide->execute([$ids['driver'],$vehicleId,$origin,$destination,$date,$time,$cost,'Demonstration route. Sample data only.']);}}
 $pdo->commit();
}catch(Throwable $error){if($pdo->inTransaction())$pdo->rollBack();fwrite(STDERR,'Seed failed: '.$error->getMessage().PHP_EOL);exit(1);}
echo "Demo accounts refreshed and sample routes are ready.".PHP_EOL;
echo "Driver: driver@mapido.local / DriverDemo!2026".PHP_EOL;
echo "Passenger: passenger@mapido.local / RiderDemo!2026".PHP_EOL;
echo "Admin: admin@mapido.local / AdminDemo!2026".PHP_EOL;
echo "Sample listings cannot be booked; publish a non-sample ride to test booking.".PHP_EOL;