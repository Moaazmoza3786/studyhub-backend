<?php
// SQL Injection Bakery - Vulnerable Search Page
// FOR EDUCATIONAL PURPOSES ONLY

$host = getenv('MYSQL_HOST') ?: 'sqli-bakery-db';
$db = getenv('MYSQL_DATABASE') ?: 'bakery';
$user = getenv('MYSQL_USER') ?: 'bakery_user';
$pass = getenv('MYSQL_PASSWORD') ?: 'bakery_pass_insecure';

$conn = new mysqli($host, $user, $pass, $db);

if ($conn->connect_error) {
    die("Connection failed");
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sweet Bakery - Search</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px;
        }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { color: white; text-align: center; margin-bottom: 30px; }
        .search-box {
            background: white;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 30px;
        }
        input[type="text"] {
            width: 80%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 10px;
            font-size: 16px;
        }
        button {
            width: 18%;
            padding: 12px;
            background: #764ba2;
            color: white;
            border: none;
            border-radius: 10px;
            cursor: pointer;
        }
        .results {
            background: white;
            padding: 20px;
            border-radius: 15px;
        }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #764ba2; color: white; }
        .error { background: #ffe0e0; color: #d63031; padding: 15px; border-radius: 10px; }
        .flag-box { background: #000; color: #0f0; padding: 20px; border-radius: 10px; font-family: monospace; margin-top: 20px; }
        .hint { color: rgba(255,255,255,0.7); text-align: center; margin-top: 20px; font-size: 14px; }
        a { color: white; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🍰 Sweet Bakery - Product Search</h1>
        
        <div class="search-box">
            <form method="GET">
                <input type="text" name="q" placeholder="Search for products..." value="<?= htmlspecialchars($_GET['q'] ?? '') ?>">
                <button type="submit">Search</button>
            </form>
        </div>
        
        <div class="results">
            <?php
            $search = $_GET['q'] ?? '';
            
            if ($search) {
                // VULNERABLE QUERY - Intentionally insecure for UNION injection!
                $query = "SELECT id, name, description, price FROM products WHERE name LIKE '%$search%' OR description LIKE '%$search%'";
                
                echo "<p><small>Query: <code>" . htmlspecialchars($query) . "</code></small></p><hr>";
                
                $result = $conn->query($query);
                
                if ($result) {
                    if ($result->num_rows > 0) {
                        echo '<table>';
                        echo '<tr><th>ID</th><th>Name</th><th>Description</th><th>Price</th></tr>';
                        
                        while ($row = $result->fetch_assoc()) {
                            echo '<tr>';
                            foreach ($row as $value) {
                                echo '<td>' . htmlspecialchars($value) . '</td>';
                            }
                            echo '</tr>';
                        }
                        echo '</table>';
                        
                        // Check if user extracted sensitive data
                        if (stripos($search, 'UNION') !== false && stripos($search, 'SELECT') !== false) {
                            echo '<div class="flag-box">';
                            echo '🚩 FLAG{Database_Dumped_3306}<br>';
                            echo 'Congratulations! You successfully performed a UNION-based SQL injection!';
                            echo '</div>';
                        }
                    } else {
                        echo '<p>No products found.</p>';
                    }
                } else {
                    echo '<div class="error">SQL Error: ' . $conn->error . '</div>';
                }
            } else {
                echo '<p>Enter a search term to find products.</p>';
            }
            ?>
        </div>
        
        <p class="hint">
            Hint: This search is vulnerable to UNION-based SQL injection.<br>
            Try: <code>' UNION SELECT 1,username,password,4 FROM users--</code><br><br>
            <a href="index.php">← Back to Login</a>
        </p>
    </div>
</body>
</html>
<?php $conn->close(); ?>
