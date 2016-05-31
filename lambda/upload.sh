#!/bin/sh

# Parse the command line arguments
UPLOAD="no"
SECURITY="sample"
LAMBDA_NAME="myTestSkill"
while getopts us:l: opt
do
  case "$opt" in
    u)  UPLOAD="yes";;
    s)  SECURITY="$OPTARG";;
    l)  LAMBDA_NAME="$OPTARG";;
    \?)
      # unknown flag
      echo >&2 "usage: $0 [-u] [-l name] [-s location]"
      echo >&2 "-u: upload to Lambda"
      echo >&2 "-l: 'name' is your Lambda function name"
      echo >&2 "-s: 'location' is security asset location (user or sample)"
      exit 1;;
  esac
done
shift `expr $OPTIND - 1`

# Security assets
# If you create your own certs/keys as per the directions in ../security/README
# then point SEC_PATH to ../security/user. This path is in the .gitignore so it
# won't be tracked by git
if [ "$SECURITY" = "user" ]; then
  SEC_PATH="../security/user"
else
  SEC_PATH="../security/sample"
fi

ROOT_CA="$SEC_PATH/rootCA.pem"
CLIENT_CERT="$SEC_PATH/client.crt"
CLIENT_KEY="$SEC_PATH/client.key"
PSK="$SEC_PATH/psk.bin"

SECURITY_FILES="$ROOT_CA $CLIENT_CERT $CLIENT_KEY $PSK"

# Python files
PYTHON_FILES="./client.py"
CONFIG="./client.cfg"

# Create a temp directory and copy everything there
if [ -d ./tmp ]; then
  echo "removing old tmp/ directory."
  rm -rf ./tmp
fi
mkdir tmp

# Make sure the files exist and copy to tmp directory
FILE_LIST="$SECURITY_FILES $PYTHON_FILES $CONFIG"
for file in $FILE_LIST
do
  if [ ! -f $file ]; then
    echo "warning: missing file $file."
  else
    cp $file ./tmp/
  fi
done

# Zip the files
ZIP_FILE=lambda_bundle.zip
if [ -f $ZIP_FILE ]; then
  echo "overwriting $ZIP_FILE."
  rm $ZIP_FILE
fi

cd tmp
echo "zipping files to $ZIP_FILE."
zip $ZIP_FILE *
mv $ZIP_FILE ../
cd ..

# Upload the zip to AWS
command -v aws >/dev/null 2>&1 || { 
  echo "AWS tools not found, skipping upload."
  UPLOAD="no"
}
if [ "$UPLOAD" = "yes" ]; then
  OUTPUT=./tmp/lambda.txt
  TIME=`date`
  DESC="ASK Lambda Function. Uploaded on $TIME"

  # Make the AWS CLI calls to upload function and edit configuration
  aws lambda update-function-code --function-name "$LAMBDA_NAME" \
    --zip-file fileb://$ZIP_FILE > $OUTPUT 2>&1
  aws lambda update-function-configuration --function-name "$LAMBDA_NAME" \
    --description "$DESC" --handler "client.lambda_handler" > $OUTPUT 2>&1
  # --timeout <seconds>
  # --memory-size <MB>

  # If needed can specify timeout/memory options. Defaults are 3 sec/128 MB
  # Lambda free tier includes 1M requests and 400,000 GB-seconds of compute time per month

  # Check that the upload was successful
  SHA_LOCAL=`openssl dgst -sha256 -binary $ZIP_FILE | openssl base64`
  SHA_LAMBDA=`cut -f1 $OUTPUT`
  ARN=`cut -f4 $OUTPUT`
  SIZE=`cut -f2 $OUTPUT`
  if [ "$SHA_LOCAL" = "$SHA_LAMBDA" ]; then
    echo "uploaded $SIZE bytes to lambda."
    echo "sha256: $SHA_LOCAL"
    echo "ARN: $ARN"
    echo "UPLOAD SUCCESS"
  else
    echo "failed to upload to lamdba!"
    cat $OUTPUT
    echo "UPLOAD FAILED"
  fi
fi

# Cleanup
echo "removing temporary files."
rm -rf ./tmp
if [ "$UPLOAD" = "no" ]; then
  echo "remember to manually upload $ZIP_FILE."
else
  rm $ZIP_FILE
fi

