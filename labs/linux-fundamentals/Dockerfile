# Linux Fundamentals Lab
# Ubuntu-based lab for basic Linux command practice

FROM ubuntu:22.04

# Set non-interactive
ENV DEBIAN_FRONTEND=noninteractive

# Install essential packages
RUN apt-get update && apt-get install -y \
    sudo \
    openssh-server \
    vim \
    nano \
    curl \
    wget \
    net-tools \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Create lab user
RUN useradd -m -s /bin/bash student && \
    echo "student:student123" | chpasswd && \
    usermod -aG sudo student

# Setup SSH
RUN mkdir /var/run/sshd && \
    sed -i 's/#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Create lab files for Task 1: Navigation
RUN mkdir -p /home/student/Documents /home/student/Downloads && \
    echo "Welcome to Linux Fundamentals Lab!" > /home/student/welcome.txt && \
    echo "You found the hidden message!" > /home/student/Documents/secret.txt

# Create log file for Task 2: grep exercise
RUN echo "[INFO] System started at 2024-01-01 10:00:00" > /home/student/logs.txt && \
    echo "[DEBUG] Loading configuration..." >> /home/student/logs.txt && \
    echo "[INFO] User login: admin" >> /home/student/logs.txt && \
    echo "[ERROR] Failed authentication attempt" >> /home/student/logs.txt && \
    echo "[INFO] password reset requested" >> /home/student/logs.txt && \
    echo "[SECRET] FLAG{Grep_Master_101}" >> /home/student/logs.txt && \
    echo "[INFO] System running normally" >> /home/student/logs.txt

# Create root secret for Task 3: sudo exercise
RUN echo "FLAG{Sudo_Power_Unleashed}" > /root/secret.txt && \
    chmod 600 /root/secret.txt

# Set proper permissions
RUN chown -R student:student /home/student

# Expose SSH
EXPOSE 22

# Start SSH
CMD ["/usr/sbin/sshd", "-D"]
