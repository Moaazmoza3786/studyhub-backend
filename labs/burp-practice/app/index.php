<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TechShop - Burp Practice</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: #1a1a2e; color: #fff; min-height: 100vh; }
        header { background: #16213e; padding: 20px; display: flex; justify-content: space-between; align-items: center; }
        h1 { color: #e94560; }
        nav a { color: #fff; margin-left: 20px; text-decoration: none; }
        .container { max-width: 1200px; margin: 40px auto; padding: 0 20px; }
        .products { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .product { background: #16213e; border-radius: 15px; padding: 20px; }
        .product img { width: 100%; height: 200px; object-fit: cover; border-radius: 10px; background: #0f3460; }
        .product h3 { margin: 15px 0 10px; color: #e94560; }
        .product .price { font-size: 24px; color: #4ecca3; font-weight: bold; }
        .product button { width: 100%; padding: 12px; margin-top: 15px; background: #e94560; color: #fff; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; }
        .product button:hover { background: #ff6b6b; }
        .flag-box { background: #000; color: #0f0; padding: 20px; border-radius: 10px; font-family: monospace; margin: 20px 0; }
        .hint { background: #0f3460; padding: 20px; border-radius: 10px; margin-top: 30px; }
        .hint h4 { color: #4ecca3; margin-bottom: 10px; }
    </style>
</head>
<body>
    <header>
        <h1>🛒 TechShop</h1>
        <nav>
            <a href="index.php">Products</a>
            <a href="cart.php">Cart</a>
            <a href="login.php">Login</a>
        </nav>
    </header>
    
    <div class="container">
        <h2 style="margin-bottom: 30px;">Featured Products</h2>
        
        <?php
        // Check for price manipulation
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $product = $_POST['product'] ?? '';
            $price = $_POST['price'] ?? 0;
            $original_price = $_POST['original_price'] ?? 0;
            
            if ($price != $original_price && $price < $original_price) {
                echo '<div class="flag-box">';
                echo '🚩 FLAG{Price_Manipulation_Is_Fun}<br>';
                echo "You changed the price from \${$original_price} to \${$price}!<br>";
                echo 'Great job intercepting and modifying the request with Burp Suite!';
                echo '</div>';
            }
        }
        ?>
        
        <div class="products">
            <div class="product">
                <div style="height: 200px; background: linear-gradient(135deg, #667eea, #764ba2); border-radius: 10px; display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 60px;">💻</span>
                </div>
                <h3>Gaming Laptop</h3>
                <p style="color: #aaa; margin-bottom: 10px;">High-performance gaming laptop</p>
                <div class="price">$1,299.99</div>
                <form method="POST">
                    <input type="hidden" name="product" value="Gaming Laptop">
                    <input type="hidden" name="price" value="1299.99">
                    <input type="hidden" name="original_price" value="1299.99">
                    <button type="submit">Buy Now</button>
                </form>
            </div>
            
            <div class="product">
                <div style="height: 200px; background: linear-gradient(135deg, #11998e, #38ef7d); border-radius: 10px; display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 60px;">🎧</span>
                </div>
                <h3>Wireless Headphones</h3>
                <p style="color: #aaa; margin-bottom: 10px;">Premium sound quality</p>
                <div class="price">$199.99</div>
                <form method="POST">
                    <input type="hidden" name="product" value="Wireless Headphones">
                    <input type="hidden" name="price" value="199.99">
                    <input type="hidden" name="original_price" value="199.99">
                    <button type="submit">Buy Now</button>
                </form>
            </div>
            
            <div class="product">
                <div style="height: 200px; background: linear-gradient(135deg, #fc4a1a, #f7b733); border-radius: 10px; display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 60px;">📱</span>
                </div>
                <h3>Smartphone Pro</h3>
                <p style="color: #aaa; margin-bottom: 10px;">Latest flagship phone</p>
                <div class="price">$999.99</div>
                <form method="POST">
                    <input type="hidden" name="product" value="Smartphone Pro">
                    <input type="hidden" name="price" value="999.99">
                    <input type="hidden" name="original_price" value="999.99">
                    <button type="submit">Buy Now</button>
                </form>
            </div>
        </div>
        
        <div class="hint">
            <h4>🎯 Task: Price Manipulation</h4>
            <p>Use Burp Suite to intercept the purchase request and change the price to something lower (like $1).</p>
            <ol style="margin-top: 10px; margin-left: 20px; color: #aaa;">
                <li>Configure your browser to use Burp Suite as a proxy</li>
                <li>Click "Buy Now" on any product</li>
                <li>Intercept the request in Burp Suite</li>
                <li>Modify the "price" parameter to a lower value</li>
                <li>Forward the modified request</li>
            </ol>
        </div>
    </div>
</body>
</html>
