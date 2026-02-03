# Eternal Blue Simulation
# Simulates a vulnerable SMB service for learning

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install Samba
RUN apt-get update && apt-get install -y \
    samba \
    smbclient \
    openssh-server \
    && rm -rf /var/lib/apt/lists/*

# Create vulnerable share
RUN mkdir -p /srv/share && \
    echo "Welcome to the vulnerable SMB share!" > /srv/share/readme.txt && \
    echo "FLAG{ETERNAL_BLUE_LOCAL_USER}" > /srv/share/user.txt && \
    echo "FLAG{ETERNAL_BLUE_SYSTEM_PWNED}" > /root/root.txt

# Configure Samba (intentionally weak)
RUN echo "[global]" > /etc/samba/smb.conf && \
    echo "workgroup = WORKGROUP" >> /etc/samba/smb.conf && \
    echo "server string = Vulnerable Server" >> /etc/samba/smb.conf && \
    echo "security = user" >> /etc/samba/smb.conf && \
    echo "map to guest = bad user" >> /etc/samba/smb.conf && \
    echo "" >> /etc/samba/smb.conf && \
    echo "[share]" >> /etc/samba/smb.conf && \
    echo "path = /srv/share" >> /etc/samba/smb.conf && \
    echo "browsable = yes" >> /etc/samba/smb.conf && \
    echo "guest ok = yes" >> /etc/samba/smb.conf && \
    echo "read only = no" >> /etc/samba/smb.conf

# Create SSH access
RUN mkdir /var/run/sshd && \
    useradd -m -s /bin/bash victim && \
    echo "victim:victim123" | chpasswd

EXPOSE 139 445 22

CMD service smbd start && service nmbd start && /usr/sbin/sshd -D
