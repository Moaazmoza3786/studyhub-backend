# Mr. Robot CTF Box
# Inspired by the TV show

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install packages
RUN apt-get update && apt-get install -y \
    apache2 \
    php \
    libapache2-mod-php \
    openssh-server \
    sudo \
    nmap \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Setup Apache
RUN a2enmod rewrite

# Create users
RUN useradd -m -s /bin/bash robot && \
    echo "robot:abcdefghijklmnopqrstuvwxyz" | chpasswd && \
    useradd -m -s /bin/bash elliot && \
    echo "elliot:ER28-0652" | chpasswd

# Setup SSH
RUN mkdir /var/run/sshd

# Create web content
RUN mkdir -p /var/www/html

# Create robots.txt (first key location hint)
RUN echo "User-agent: *" > /var/www/html/robots.txt && \
    echo "Disallow: /key-1-of-3.txt" >> /var/www/html/robots.txt && \
    echo "Disallow: /fsociety.dic" >> /var/www/html/robots.txt

# Create first key
RUN echo "073403c8a58a1f80d943455fb30724b9" > /var/www/html/key-1-of-3.txt

# Create dictionary file
RUN echo "admin" > /var/www/html/fsociety.dic && \
    echo "password" >> /var/www/html/fsociety.dic && \
    echo "letmein" >> /var/www/html/fsociety.dic && \
    echo "elliot" >> /var/www/html/fsociety.dic && \
    echo "mrrobot" >> /var/www/html/fsociety.dic && \
    echo "fsociety" >> /var/www/html/fsociety.dic && \
    echo "ER28-0652" >> /var/www/html/fsociety.dic

# Create second key (user flag)
RUN echo "FLAG{MR_ROBOT_USER_KEY_2}" > /home/robot/key-2-of-3.txt && \
    chown robot:robot /home/robot/key-2-of-3.txt && \
    chmod 400 /home/robot/key-2-of-3.txt

# Create third key (root flag)
RUN echo "FLAG{MR_ROBOT_ROOT_KEY_3}" > /root/key-3-of-3.txt && \
    chmod 600 /root/key-3-of-3.txt

# Create SUID binary for privesc
RUN chmod u+s /usr/bin/nmap

# Create simple index page
RUN echo '<!DOCTYPE html><html><head><title>Mr Robot</title><style>body{background:#000;color:#0f0;font-family:monospace;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}h1{font-size:48px;}</style></head><body><h1>ARE YOU A 1 OR A 0?</h1></body></html>' > /var/www/html/index.html

# Set permissions
RUN chown -R www-data:www-data /var/www/html

EXPOSE 80 22

CMD service apache2 start && /usr/sbin/sshd -D
