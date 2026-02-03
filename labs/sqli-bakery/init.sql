-- SQL Injection Bakery Database
-- Vulnerable by design for learning

CREATE DATABASE IF NOT EXISTS bakery;
USE bakery;

-- Users table (vulnerable)
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products table
CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    category VARCHAR(50),
    image_url VARCHAR(255)
);

-- Orders table
CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    product_id INT,
    quantity INT DEFAULT 1,
    total_price DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample users
INSERT INTO users (username, password, email, role) VALUES
('admin', 'admin123', 'admin@bakery.local', 'admin'),
('manager', 'manager456', 'manager@bakery.local', 'manager'),
('john', 'password123', 'john@example.com', 'user'),
('FLAG_USER', 'FLAG{Database_Dumped_3306}', 'flag@secret.local', 'hidden');

-- Insert sample products
INSERT INTO products (name, description, price, category) VALUES
('Chocolate Cake', 'Delicious chocolate layer cake', 25.99, 'cakes'),
('Croissant', 'Fresh butter croissant', 3.50, 'pastries'),
('Baguette', 'Traditional French bread', 4.00, 'bread'),
('Apple Pie', 'Homemade apple pie', 15.99, 'pies'),
('Cinnamon Roll', 'Sweet cinnamon swirl', 4.50, 'pastries');

-- Create a secret table
CREATE TABLE secrets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    flag VARCHAR(255) NOT NULL,
    hint VARCHAR(255)
);

INSERT INTO secrets (flag, hint) VALUES
('FLAG{Login_Bypassed_Succesfully}', 'You bypassed authentication!'),
('FLAG{Database_Dumped_3306}', 'You extracted the database!');
