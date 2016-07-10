#!/bin/sh

# Set some default values
STREAMS=1
LAMBDA_NAME="myTestSkill"

# Parse the command line arguments
while getopts s:l: opt
do
  case "$opt" in
    s)  STREAMS=$OPTARG;;
    l)  LAMBDA_NAME="$OPTARG";;
    \?)
      # unknown flag
      echo >&2 "usage: $0 [-l name] [-s streams]"
      echo >&2 "-l: 'name' is your Lambda function name"
      echo >&2 "-s: number of latest streams to pull (default 1)"
      exit 1;;
  esac
done
shift `expr $OPTIND - 1`

# Check to make sure CLI tools are installed
command -v aws >/dev/null 2>&1 || { 
  echo "AWS tools not found, please install."
  exit 1
}

# Get the log file name to write data to
TIME=`date +%F_%H%M%S`
LOGFILE="./logs/$TIME.txt"
if [ -f $LOGFILE ]; then
    echo "Overwriting $LOGFILE"
    rm $LOGFILE
fi

# Grab all the streams available for this log group
STREAM_NAMES=`aws logs describe-log-streams --log-group-name "/aws/lambda/$LAMBDA_NAME" --order-by "LastEventTime" --descending | cut -f7 -`

STREAM_CNT=`echo $STREAM_NAMES | wc -w`
echo "Available streams: $STREAM_CNT"

# For each stream, grab the events and output to log file
CNT=0
echo "Writing event data to $LOGFILE"
for stream in $STREAM_NAMES
do
    echo "Getting events from stream '$stream'"

    # Write events from each stream into log file
    EVENTS=`aws logs get-log-events --log-group-name "/aws/lambda/$LAMBDA_NAME" --log-stream-name "$stream" | cut -f3-`
    echo "$EVENTS" >> $LOGFILE

    CNT=$((CNT+1))
    if [ $CNT -ge $STREAMS ]; then
        break
    fi
done

# Cleanup log file by removing blank lines
grep -v '^$' $LOGFILE > ./logs/tmp
mv ./logs/tmp $LOGFILE