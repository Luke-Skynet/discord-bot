FROM --platform=linux/amd64 ubuntu:22.04

RUN apt update && apt upgrade -y \
    && apt install -y build-essential \
    && apt install -y wget \
    && apt install -y git \
    && apt install -y ffmpeg \
    && apt install -y opus-tools \
    && apt clean \
    && rm -rf /var/lib/apt/lists/*

ENV CONDA_DIR /opt/conda

RUN COMPARCH=x86_64; \
    if ["$BUILDARCH" = "arm64" ]; then COMPARCH=aarch64; fi; \
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-$COMPARCH.sh -O ~/miniconda.sh && \
    /bin/bash ~/miniconda.sh -b -p /opt/conda

ENV PATH $CONDA_DIR/bin:$PATH

RUN git clone https://github.com/Luke-Skynet/discord-bot.git ~/discord-bot; \
    cd ~/discord-bot;

RUN conda install -y pip; \
    pip install -r ~/discord-bot/requirements.txt;

