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

#finally copy over codebase
COPY . /root/discord-bot
