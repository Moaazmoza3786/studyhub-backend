# Privilege Escalation Lab
# Linux box with SUID misconfiguration

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install packages
RUN apt-get update && apt-get install -y \
    sudo \
    openssh-server \
    python3 \
    vim \
    nano \
    curl \
    wget \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Create lab user (no sudo)
RUN useradd -m -s /bin/bash student && \
    echo "student:student123" | chpasswd

# Setup SSH
RUN mkdir /var/run/sshd

# Create SUID vulnerability - Python3 with SUID bit
# This is intentionally misconfigured for the lab
RUN chmod u+s /usr/bin/python3

# Create flag file
RUN echo "FLAG{Root_Access_Granted_King}" > /root/flag.txt && \
    chmod 600 /root/flag.txt

# Create hint files
RUN echo "Welcome to the Privilege Escalation Lab!" > /home/student/README.txt && \
    echo "" >> /home/student/README.txt && \
    echo "Your goal: Get root access and read /root/flag.txt" >> /home/student/README.txt && \
    echo "" >> /home/student/README.txt && \
    echo "Hints:" >> /home/student/README.txt && \
    echo "1. Look for SUID binaries: find / -perm -4000 2>/dev/null" >> /home/student/README.txt && \
    echo "2. Check GTFOBins for exploitation techniques" >> /home/student/README.txt && \
    echo "3. Python can spawn a shell with os.execl" >> /home/student/README.txt

# Set permissions
RUN chown -R student:student /home/student

EXPOSE 22

CMD ["/usr/sbin/sshd", "-D"]
