FROM ubuntu:latest
LABEL authors="merynov"

ENTRYPOINT ["top", "-b"]