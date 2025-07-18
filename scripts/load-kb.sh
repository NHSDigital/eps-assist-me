#!/bin/bash

#==============================================================================
#title           : load-kb.sh

#description     :
# This script will upload the AWS Well architected Framework pillar documents 
# to the given s3 Bucket then sync the Amazon Bedrock Knowledgebase

# Params          :
# Param01: The Amazon Bedrock Knowledge Base ID. e.g ZJIPCAGXUG
# Param02: The Amazon Bedrock Knowledge Base Data Source ID - expect to be backed by the above S3 Doc store
# Param03: Amazon S3 URI for uploading KB docs e.g. s3://my-bucket/my-prefix/

#usage		     : ./load-kb.sh knowledgebase-id knowledgebase-data-source-id s3-bucket-prefix 
# e.g            : ./load-kb.sh ZJIPCAGXUG LJIQHHG7PR s3://kb-bucket/aws-war-bot/ 

#==============================================================================


set -e -x

# check that we have the right number of parameters
if [ $# -ne 3 ]; then
    echo "Usage: $0 <kb-id> <data-source-id> <s3-bucket/prefix/>"
    exit 1
fi

# Assign positional params to loval vars
KB_ID=$1
DS_ID=$2
S3_URI=$3

# AWS Well Architceted Framework Pillar documents
DOC_LIST=(
  "https://docs.aws.amazon.com/pdfs/wellarchitected/latest/framework/wellarchitected-framework.pdf"
  "https://docs.aws.amazon.com/pdfs/wellarchitected/latest/reliability-pillar/wellarchitected-reliability-pillar.pdf"
  "https://docs.aws.amazon.com/pdfs/wellarchitected/latest/security-pillar/wellarchitected-security-pillar.pdf"
  "https://docs.aws.amazon.com/pdfs/wellarchitected/latest/performance-efficiency-pillar/wellarchitected-performance-efficiency-pillar.pdf"
  "https://docs.aws.amazon.com/pdfs/wellarchitected/latest/operational-excellence-pillar/wellarchitected-operational-excellence-pillar.pdf"
  "https://docs.aws.amazon.com/pdfs/wellarchitected/latest/cost-optimization-pillar/wellarchitected-cost-optimization-pillar.pdf"
  "https://docs.aws.amazon.com/pdfs/wellarchitected/latest/sustainability-pillar/wellarchitected-sustainability-pillar.pdf"
  )

# make a temporary directory to download the AWS Well Architceted Framework Pillar documents
DOCS_DIR='./aws-well-architected-docs'
mkdir $DOCS_DIR

pushd $DOCS_DIR

# download the docs
for doc in "${DOC_LIST[@]}"
do
  curl -L -o "$DOCS_DIR/$(basename $doc)" $doc
done

aws s3 sync $DOCS_DIR $S3_URI
# popd
rm -rf $DOCS_DIR

# sync kb
aws bedrock-agent start-ingestion-job --knowledge-base-id $KB_ID --data-source-id $DS_ID
