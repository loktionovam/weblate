#!/usr/bin/env bash

export USER_ID=$(id -u)
export GROUP_ID=$(id -g)
export WEBLATE_HOST=127.0.0.1:8080

cd dev-docker/

docker-compose rm --stop -v

for VOLUME in $(docker-compose config --volumes); do
    if docker volume ls | grep "${VOLUME}"; then
        docker volume rm "$(docker volume ls | grep "${VOLUME}" | awk '{print $2}')"
    fi
done
