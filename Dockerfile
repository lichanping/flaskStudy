# syntax=docker/dockerfile:1

FROM python:3.10-slim-buster

RUN apt update && apt install -y cmake g++ make ffmpeg libsm6 libxext6 wget

WORKDIR /python-docker

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

ENV IN_DOCKER=true

CMD [ "python3", "-m" , "flask", "--app", "app", "run", "--host", "0.0.0.0"]
