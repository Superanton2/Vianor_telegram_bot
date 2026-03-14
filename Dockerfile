FROM ubuntu:latest
LABEL authors="home"

ENTRYPOINT ["top", "-b"]