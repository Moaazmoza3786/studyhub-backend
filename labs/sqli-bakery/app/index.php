<?php
// SQL Injection Bakery - Vulnerable Web Application
// FOR EDUCATIONAL PURPOSES ONLY

$host = getenv('MYSQL_HOST') ?: 'sqli-bakery-db';
$db = getenv('MYSQL_DATABASE') ?: 'bakery';
$user = getenv('MYSQL_USER') ?: 'bakery_user';
$pass = getenv('MYSQL_PASSWORD') ?: 'bakery_pass_insecure';

$conn = new mysqli($host, $user, $pass, $db);

if ($conn->connect_error) {
    die("Connection failed - Database not ready yet");
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sweet Bakery - Login</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            width: 400px;
        }
        h1 { color: #764ba2; text-align: center; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; color: #333; font-weight: 600; }
        input[type="text"], input[type="password"] {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #ddd;
            border-radius: 10px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        input:focus { outline: none; border-color: #764ba2; }
        button {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.3s;
        }
        button:hover { transform: translateY(-2px); }
        .error { background: #ffe0e0; color: #d63031; padding: 15px; border-radius: 10px; margin-bottom: 20px; }
        .success { background: #d4edda; color: #155724; padding: 15px; border-radius: 10px; margin-bottom: 20px; }
        .flag-box { background: #000; color: #0f0; padding: 20px; border-radius: 10px; font-family: monospace; margin-top: 20px; }
        .hint { font-size: 12px; color: #999; margin-top: 20px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🍰 Sweet Bakery</h1>
        
        <?php
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $username = $_POST['username'] ?? '';
            $password = $_POST['password'] ?? '';
            
            // VULNERABLE QUERY - Intentionally insecure!
            $query = "SELECT * FROM users WHERE username='$username' AND password='$password'";
            
            $result = $conn->query($query);
            
            if ($result && $result->num_rows > 0) {
                $user = $result->fetch_assoc();
                echo '<div class="success">';
                echo '<strong>Welcome, ' . htmlspecialchars($user['username']) . '!</strong><br>';
                echo 'Role: ' . htmlspecialchars($user['role']);
                echo '</div>';
                
                if ($user['role'] === 'admin' || strpos($username, "'") !== false) {
                    echo '<div class="flag-box">';
                    echo '🚩 FLAG{Login_Bypassed_Succesfully}';
                    echo '</div>';
                }
            } else {
                echo '<div class="error">Invalid username or password!</div>';
            }
        }
        ?>
        
        <form method="POST">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" placeholder="Enter username" required>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" placeholder="Enter password" required>
            </div>
            <button type="submit">Login</button>
        </form>
        
        <p class="hint">
            Hint: Try SQL injection techniques to bypass authentication<br>
            Example: ' OR 1=1--
        </p>
        
        <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
        
        <h3 style="color: #764ba2; margin-bottom: 15px;">🔍 Product Search</h3>
        <form method="GET" action="search.php">
            <input type="text" name="q" placeholder="Search products..." style="width: 70%;">
            <button type="submit" style="width: 25%; margin-left: 5%;">Search</button>
        </form>
    </div>
</body>
</html>
<?php $conn->close(); ?>
