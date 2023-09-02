#AWS usually uses intel/amd systems so go with that
FROM --platform=linux/amd64 ubuntu:22.04

#set up linux libraries and install python
RUN apt update && apt upgrade -y \
    && apt install -y build-essential \
    && apt install -y wget curl gnupg \
    && apt install -y python3 python3-pip git \
    && apt install -y ffmpeg opus-tools \
    && apt clean \
    && rm -rf /var/lib/apt/lists/*

#needed to autoinstall the rest in a docker env
ARG DEBIAN_FRONTEND=noninteractive

#install python libraries before mongodb
COPY requirements.txt .
RUN pip install -r requirements.txt

#install mongodb
RUN curl -fsSL https://pgp.mongodb.com/server-6.0.asc | \
    gpg -o /usr/share/keyrings/mongodb-server-6.0.gpg \
    --dearmor; \
    echo "deb [ arch=amd64 signed-by=/usr/share/keyrings/mongodb-server-6.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/6.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-6.0.list; \
    apt update; \
    apt install -y mongodb-org

#finally copy over codebase
COPY . /root/discord-bot
