ARG PYTHON_BASE_IMAGE=docker.m.daocloud.io/library/python:3.11.7-slim
FROM ${PYTHON_BASE_IMAGE}

RUN printf '%s\n' \
    "deb http://mirrors.aliyun.com/debian/ bookworm main non-free non-free-firmware contrib" \
    "deb http://mirrors.aliyun.com/debian-security bookworm-security main non-free non-free-firmware contrib" \
    "deb http://mirrors.aliyun.com/debian/ bookworm-updates main non-free non-free-firmware contrib" \
    > /etc/apt/sources.list

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        python3-dev \
        make \
        libgl1 \
        libgl1-mesa-glx \
        libglu1-mesa \
        libglib2.0-0 \
        libfontconfig1 \
        libfreetype6 \
        libxrender1 \
        libxext6 \
        libx11-6 \
        fonts-dejavu-core \
        fonts-liberation \
        fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

RUN pip config set global.index-url "https://mirrors.cernet.edu.cn/pypi/web/simple" && \
    pip install --upgrade pip setuptools wheel

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

RUN chmod -R 755 /app
