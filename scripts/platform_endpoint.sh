#!/bin/bash

MD_PLATFORM_HOST=${MD_PLATFORM_HOST:-localhost}
MD_PLATFORM_PORT=${MD_PLATFORM_PORT:-80}

echo "--> Using md_platform on $MD_PLATFORM_HOST:$MD_PLATFORM_PORT"
echo "... (please configure MD_PLATFORM_HOST and MD_PLATFORM_PORT if you don't agree) ..."

command -v curl > /dev/null

if [ $? -eq 0 ]; then
    echo -e "Checking presence of curl ... \e[32mOK\e[0m"
else
    echo -e "Checking presence of curl ... \e[31mFAIL\e[0m"
    echo "This program needs curl, please install it first."
    exit -1
fi

command -v jq > /dev/null

if [ $? -eq 0 ]; then
    echo -e "Checking presence of jq ... \e[32mOK\e[0m"
else
    echo -e "Checking presence of jq ... \e[31mFAIL\e[0m"
    echo "This program needs jq, please install it first."
    exit -1
fi 

ENDPOINT=$1
if [[ $ENDPOINT = /* ]]; then
    echo -e "Checking validity of endpoint argument ... \e[32mOK\e[0m"
else
    echo -e "Checking validity of endpoint argument ... \e[31mFAIL\e[0m"
    echo "The argument to this program should be a relative endpoint e.g. /accounting_report"
    exit -1
fi

if [ -z "$MD_PLATFORM_USER" ]; then
    echo -e "Checking credentials  ... \e[31mFAIL\e[0m"
    echo -e "\e[31mPlease set the environment variable MD_PLATFORM_USER\e[0m."
    exit -1
fi

if [ -z "$MD_PLATFORM_PASSWORD" ]; then
    echo -e "Checking credentials  ... \e[31mFAIL\e[0m"
    echo -e "\e[31mPlease set the environment variable MD_PLATFORM_PASSWORD.\e[0m"
    exit -1
fi

echo -e "Checking credentials  ...  \e[32mOK\e[0m"

JSON_TOKEN=$(curl -s -u $MD_PLATFORM_USER:$MD_PLATFORM_PASSWORD http://${MD_PLATFORM_HOST}:${MD_PLATFORM_PORT}/authenticate | jq -r '.token')
echo ""

ENDPOINT_REQUEST="curl -H \"Authorization: Bearer ${JSON_TOKEN}\" http://${MD_PLATFORM_HOST}:${MD_PLATFORM_PORT}${ENDPOINT}"
echo $ENDPOINT_REQUEST