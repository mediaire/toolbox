#!/bin/bash

# ============================================================================
# Command line tool that can be used to query the platform via command line
# when authentication is enabled.
# Basic Auth login is performed using the environment variables 
# MD_PLATFORM_USER and MD_PLATFORM_PASSWORD.
# It will fetch a JWT token using the provided credentials and use it with
# Bearer authentication to execute the provided endpoint as argument.
#
# Example usage:
# 
# ./platform_endpoint.sh "/accounting_report"
#
# By default it assumes a GET request. To execute a POST request:
#
# ./platform_endpoint.sh "/accounting_report" POST
# ============================================================================

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
METHOD=${2:-GET}

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

ENDPOINT_REQUEST="curl -X ${METHOD} -H \"Authorization: Bearer ${JSON_TOKEN}\" http://${MD_PLATFORM_HOST}:${MD_PLATFORM_PORT}${ENDPOINT}"

eval $ENDPOINT_REQUEST