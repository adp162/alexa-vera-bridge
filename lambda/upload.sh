#!/bin/sh

# Security assets
# If you create your own certs/keys as per the directions in ../security/README
# then point SEC_PATH to ../security/user. This path is in the .gitignore so it
# won't be tracked by git

#SEC_PATH="../security/user"
SEC_PATH="../security/sample"

ROOT_CA="$SEC_PATH/rootCA.pem"
CLIENT_CERT="$SEC_PATH/client.crt"
CLIENT_KEY="$SEC_PATH/client.key"
PSK="$SEC_PATH/psk.bin"

SECURITY_FILES="$ROOT_CA $CLIENT_CERT $CLIENT_KEY"

# Python files
PYTHON_FILES="./client.py"
CONFIG="./client.cfg"

# Make sure the files exist
FILE_LIST="$SECURITY_FILES $PYTHON_FILES $CONFIG"
for file in $FILE_LIST
do
  if [ ! -f $file ]; then
    echo "missing file $file."
    exit
  fi
done

# Create a temp directory and copy everything there
if [ -d ./tmp ]; then
  echo "removing old tmp/ directory."
  rm -rf ./tmp
fi
mkdir tmp
cp $FILE_LIST ./tmp/

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
UPLOAD="yes"
command -v aws >/dev/null 2>&1 || { 
  echo "AWS tools not found, skipping upload."
  UPLOAD="no"
}
if [ "$UPLOAD" = "yes" ]; then
  # Change this name to match the name of your Lambda function
  LAMBDA_NAME=myTestSkill
  OUTPUT=./tmp/lambda.txt

  aws lambda update-function-code --function-name $LAMBDA_NAME --zip-file fileb://$ZIP_FILE > $OUTPUT 2>&1

  # Check that the upload was successful
  SHA_LOCAL=`openssl sha256 -binary $ZIP_FILE | openssl base64`
  SHA_LAMBDA=`cut -f1 $OUTPUT`
  ARN=`cut -f4 $OUTPUT`
  SIZE=`cut -f2 $OUTPUT`
  if [ "$SHA_LOCAL" = "$SHA_LAMBDA" ]; then
    echo "successfully uploaded $SIZE bytes to lambda."
    echo "ARN: $ARN"
  else
    echo "failed to upload to lamdba!"
    cat $OUTPUT
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

