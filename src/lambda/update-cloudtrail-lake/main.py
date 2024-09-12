'''
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import logging
import json
import os
import uuid
import boto3
import traceback
from dateutil.parser import parse
from botocore.exceptions import ClientError


# CloudTrail Lake options
CLOUDTRAIL_LAKE_CHANNEL_ARN = os.environ["CLOUDTRAIL_LAKE_CHANNEL_ARN"]
DEFAULT_USER_TYPE = os.environ.get("DEFAULT_USER_TYPE", "MSAzureUser")


# Logging options
logging.basicConfig()
logger = logging.getLogger()
if 'LOG_LEVEL' in os.environ:
  logger.setLevel(os.environ["LOG_LEVEL"])
  logger.info(f"Log level set to {logger.getEffectiveLevel()}")
else:
  logger.setLevel(logging.INFO)


# Boto3 resources
session = boto3.Session()
sts_client = session.client('sts')
cloudtrail_client = session.client('cloudtrail-data')
sqs_client = session.client('sqs')
RECIPIENT_ACCOUNT_ID = sts_client.get_caller_identity()['Account']



def transform_entry(entry: dict):

  if entry.get("properties").get("eventCategory") != "Administrative":
    logger.info(f"Skipping non-Administrative log entry: {entry}")
    return None

  uid = "{}-{}".format(entry.get("correlationId"), str(uuid.uuid4()))
  event_version = entry.get("ReleaseVersion")
  user_type = DEFAULT_USER_TYPE
  user_id = entry.get("identity").get("claims").get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/upn", "None")
  user_details = entry.get("identity", "None")
  event_source = entry.get("resourceId")
  event_name = entry.get("operationName")
  event_time = entry.get("time")
  user_agent = "None"
  source_ip = entry.get("callerIpAddress")
  recipient_account_id = entry.get("tenantId")
  request_params = {}
  response_elements ={}
  resource = entry.get("properties")

  event = {
    "version": event_version,
    "userIdentity": {
      "type": user_type,
      "principalId": user_id,
      "details": user_details
    },
    "userAgent": user_agent,
    "eventSource": event_source,
    "eventName": event_name,
    "eventTime": parse(event_time).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "UID": uid,
    "requestParameters": request_params,
    "responseElements": response_elements,
    "sourceIPAddress": source_ip,
    "recipientAccountId": RECIPIENT_ACCOUNT_ID,
    "additionalEventData": resource
  }

  logger.debug(f"Transformed entry: {event}")

  audit_event = {
    "eventData": json.dumps(event),
    "id": uid
  }

  return audit_event



def ingest_data(data: list):

  try:
    output = cloudtrail_client.put_audit_events(
      auditEvents=data,
      channelArn= CLOUDTRAIL_LAKE_CHANNEL_ARN
      )
    success = True
    
    if len(output['failed']) > 0:
      success = False
    return {'result': success, 'failed': output['failed'], 'successful': output['successful']}

  except ClientError as err:
    logger.error(f"Failed to put events: {traceback.format_exc()}")
    raise err



def lambda_handler(event, context):

  sqs_messages = event.get("Records")
  sqs_all_msg_body = list()
  audit_events = list()

  try:
    for sqs_msg in sqs_messages:
      sqs_msg_body = sqs_msg.get("body")
      sqs_msg_data_json = json.loads(sqs_msg_body)
      msg_data = sqs_msg_data_json.get("records")
      if msg_data is None:
        logger.error(f"Skipping entry because inconsistent data: {sqs_msg}")
        continue
      for data in msg_data:
        sqs_all_msg_body.append(data)

  except:
    logger.info("No audit events were found to ingest from the SQS message. Quitting.")
    return None

  if len(sqs_all_msg_body) == 0:
    logger.info("No audit events were found to ingest, because there are no items on the list. Quitting.")
    return None
  
  if len(sqs_all_msg_body) == 1:
    event = transform_entry(sqs_all_msg_body[0])
    if event is None:
      logger.error("Skipping entry because transform failed")
      return None
    audit_events.append(event)
  
  if len(sqs_all_msg_body) > 1:
    for m in sqs_all_msg_body:
      event = transform_entry(m)
      if event is None:
        logger.error("Skipping entry because transform failed")
        continue
      audit_events.append(event)

  try:
    response = ingest_data(audit_events)
    print(response)
  
  except:
    logger.error(f"Failed to ingest data: {traceback.format_exc()}")
    return None