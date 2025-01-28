#!/bin/bash

COLOR_OFF="\033[0m"
RED="\033[0;31m"
GREEN="\033[0;32m"
BROWN="\033[0;33m"
BROWN="\033[0;34m"

if [ $1 == '--start_dev' ]
then

    printf "${GREEN}Starting development environment${COLOR_OFF}\n"
    docker compose -f docker-compose.yaml up -d --build
    sudo chmod -R go+w ../../

elif [ $1 == '--close_dev' ]
then

    printf "${RED}Closing development environment${COLOR_OFF}\n"
    docker compose -f docker-compose.yaml down

elif [ $1 == '--help' ]
then
    printf "${GREEN}Options:
        --start_dev Start development environment
        --close_dev Close development environment
        ${COLOR_OFF}\n"

else
    printf "${RED}Error: Invalid option. Type '$0 --help' for avaliable options\n"
    exit 1
fi
