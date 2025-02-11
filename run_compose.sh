#!/bin/bash

xhost +local:

export ROS_DISTRO="noetic"

docker-compose up --remove-orphans
docker-compose -f docker-compose.yml up


# Connect to containers by running the following in 
# a new terminal:
# docker exec -it [container_name] bash
# for example:
# docker exec -it harmoni_full bash
