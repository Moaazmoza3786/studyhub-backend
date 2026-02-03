# SQL Injection Bakery Lab
# Vulnerable web application for SQLi practice

FROM php:8.1-apache

# Install MySQL client and PHP extensions
RUN docker-php-ext-install mysqli pdo pdo_mysql && \
    a2enmod rewrite

# Copy application files
COPY app/ /var/www/html/

# Create application directory structure
RUN mkdir -p /var/www/html

# Set permissions
RUN chown -R www-data:www-data /var/www/html && \
    chmod -R 755 /var/www/html

EXPOSE 80

CMD ["apache2-foreground"]
