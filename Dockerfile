# AWS usually uses intel/amd systems so go with that
FROM --platform=linux/amd64 ubuntu:22.04

# Set non-interactive mode
ENV DEBIAN_FRONTEND=noninteractive

# set up linux libraries and install python3.11
RUN apt update && apt upgrade -y \
    && apt install -y build-essential \
    && apt install -y wget curl gnupg \
    && apt install -y python3-pip \
    && apt install -y ffmpeg opus-tools \
    && apt clean \
    && rm -rf /var/lib/apt/lists/*

# install python libraries
COPY requirements.txt .
RUN pip install -r requirements.txt

# finally copy over codebase
COPY . /root/discord-bot
