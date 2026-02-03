# Networking 101 Lab
# Network diagnostics practice environment

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install networking tools
RUN apt-get update && apt-get install -y \
    openssh-server \
    iputils-ping \
    traceroute \
    telnet \
    netcat \
    nmap \
    dnsutils \
    net-tools \
    tcpdump \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create lab user
RUN useradd -m -s /bin/bash student && \
    echo "student:student123" | chpasswd

# Setup SSH
RUN mkdir /var/run/sshd

# Create network lab files
RUN echo "Network Lab - Test your networking skills!" > /home/student/README.txt && \
    echo "Target: 10.10.10.5" >> /home/student/README.txt && \
    echo "Tasks:" >> /home/student/README.txt && \
    echo "1. Ping the target" >> /home/student/README.txt && \
    echo "2. Trace the route" >> /home/student/README.txt

# Set permissions
RUN chown -R student:student /home/student

EXPOSE 22

CMD ["/usr/sbin/sshd", "-D"]
