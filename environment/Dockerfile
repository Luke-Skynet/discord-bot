FROM --platform=linux/amd64 ubuntu:22.04

RUN apt update && apt upgrade -y \
    && apt install -y build-essential \
    && apt install -y wget curl gnupg\
    && apt install -y git \
    && apt install -y ffmpeg \
    && apt install -y opus-tools \
    && apt clean \
    && rm -rf /var/lib/apt/lists/*

ARG DEBIAN_FRONTEND=noninteractive

run curl -fsSL https://pgp.mongodb.com/server-6.0.asc | \
    gpg -o /usr/share/keyrings/mongodb-server-6.0.gpg \
    --dearmor; \
    echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-6.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/6.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-6.0.list; \
    apt update; \
    apt install -y mongodb-org

ENV CONDA_DIR /opt/conda

RUN COMPARCH=x86_64; \
    if ["$BUILDARCH" = "arm64" ]; then COMPARCH=aarch64; fi; \
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-$COMPARCH.sh -O ~/miniconda.sh && \
    /bin/bash ~/miniconda.sh -b -p /opt/conda

ENV PATH $CONDA_DIR/bin:$PATH

RUN git clone https://github.com/Luke-Skynet/discord-bot.git ~/discord-bot;

RUN conda install -y pip; \
    pip install -r ~/discord-bot/environment/requirements.txt;

RUN mkdir -p /data/db

CMD ["mongod",]