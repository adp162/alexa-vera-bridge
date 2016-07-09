#!/bin/sh

# Set some default values
ALL="no"
EVENTS="10"
LAMBDA_NAME="myTestSkill"

# Parse the command line arguments
while getopts ae:l: opt
do
  case "$opt" in
    a)  ALL="yes";;
    e)  EVENTS="$OPTARG";;
    l)  LAMBDA_NAME="$OPTARG";;
    c)  CONFIG="$OPTARG";;
    \?)
      # unknown flag
      echo >&2 "usage: $0 [-a] [-l name] [-e events]"
      echo >&2 "-a: pull all logs"
      echo >&2 "-l: 'name' is your Lambda function name"
      echo >&2 "-e: number of latest events to pull (default 10)"
      exit 1;;
  esac
done
shift `expr $OPTIND - 1`

# Check to make sure CLI tools are installed
command -v aws >/dev/null 2>&1 || { 
  echo "AWS tools not found, please install."
  exit 1
}

# Make the AWS CLI call to pull the logs
if [ "$ALL" = "no" ]; then
  LIMIT="--limit $EVENTS"
fi

aws logs get-log-events --log-group-name "/aws/lambda/$LAMBDA_NAME" \
    --log-stream-name "20150601" \
    $LIMIT

