<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TechShop - Login</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: #1a1a2e; color: #fff; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .container { background: #16213e; padding: 40px; border-radius: 20px; width: 400px; }
        h1 { color: #e94560; text-align: center; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; color: #aaa; }
        input { width: 100%; padding: 12px; border: 2px solid #0f3460; background: #0f3460; color: #fff; border-radius: 8px; font-size: 16px; }
        input:focus { outline: none; border-color: #e94560; }
        button { width: 100%; padding: 15px; background: #e94560; color: #fff; border: none; border-radius: 8px; font-size: 18px; cursor: pointer; }
        button:hover { background: #ff6b6b; }
        .error { background: #ff6b6b22; border: 1px solid #ff6b6b; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .success { background: #4ecca322; border: 1px solid #4ecca3; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .hint { background: #0f3460; padding: 15px; border-radius: 8px; margin-top: 20px; font-size: 14px; color: #aaa; }
        a { color: #e94560; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔐 Admin Login</h1>
        
        <?php
        // Common passwords for brute force challenge
        $valid_passwords = ['sunshine', 'password123', 'admin', 'letmein', '123456'];
        $admin_password = 'sunshine'; // The correct one
        
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $username = $_POST['username'] ?? '';
            $password = $_POST['password'] ?? '';
            
            if ($username === 'admin' && $password === $admin_password) {
                echo '<div class="success">';
                echo '✅ Login successful!<br>';
                echo 'Password found: <strong>' . $password . '</strong>';
                echo '</div>';
            } else {
                echo '<div class="error">';
                echo '❌ Invalid credentials';
                echo '</div>';
            }
        }
        ?>
        
        <form method="POST">
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" value="admin" readonly>
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" placeholder="Enter password">
            </div>
            <button type="submit">Login</button>
        </form>
        
        <div class="hint">
            <h4 style="color: #4ecca3; margin-bottom: 10px;">🎯 Task: Brute Force with Intruder</h4>
            <p>Use Burp Intruder to brute force the admin password using a common password list.</p>
            <ol style="margin-top: 10px; margin-left: 20px;">
                <li>Capture the login request in Burp Proxy</li>
                <li>Send it to Intruder</li>
                <li>Set the password field as the payload position</li>
                <li>Load a password list (try rockyou-top1000)</li>
                <li>Start the attack and look for different response lengths</li>
            </ol>
            <p style="margin-top: 10px;"><a href="index.php">← Back to Shop</a></p>
        </div>
    </div>
</body>
</html>
