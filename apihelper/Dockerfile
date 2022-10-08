FROM python:3.9


RUN mkdir -p /usr/src/app

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get -y update
RUN apt-get install -y \
    build-essential cmake pkg-config git unzip wget \
    libjpeg-dev libtiff5-dev libpng-dev \
    ffmpeg libavcodec-dev libavformat-dev libswscale-dev libxvidcore-dev libx264-dev libxine2-dev \
    libv4l-dev v4l-utils \
    libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
    libgtk-3-dev \
    mesa-utils libgl1-mesa-dri libgtkgl2.0-dev libgtkglext1-dev \
    libatlas-base-dev gfortran libeigen3-dev \
    wkhtmltopdf

RUN pip install --upgrade pip


COPY requirements.txt requirements.txt
COPY requirements-dev.txt requirements-dev.txt


RUN pip install -r requirements.txt
RUN pip install -r requirements-dev.txt

COPY . /usr/src/app

