const { EventHubConsumerClient, earliestEventPosition  } = require("@azure/event-hubs");
const { ContainerClient } = require("@azure/storage-blob");    
const { BlobCheckpointStore } = require("@azure/eventhubs-checkpointstore-blob");
const AWS = require('aws-sdk');
const { SecretsManagerClient, GetSecretValueCommand } = require("@aws-sdk/client-secrets-manager");


AWS.config.region = process.env.AWS_REGION;
const sqs = new AWS.SQS({apiVersion: '2012-11-05'});
// const secrets = new AWS.SecretsManager({apiVersion: '2017-10-17'});
const secretsClient = new SecretsManagerClient({ region: process.env.AWS_REGION });

const secretName = process.env.SECRET_NAME;
const sqsQueneName = process.env.SQS_QUEUE_NAME;
const eventHubNamespace = process.env.AZURE_EVENTHUBS_NAMESPACE;
const eventHubName = process.env.AZURE_EVENTHUBS_NAME;
const eventHubSharedAccessPolicyName = process.env.AZURE_EVENTHUBS_SHARED_ACCESS_POLICY_NAME;
const consumerGroup = process.env.AZURE_EVENTHUBS_CONSUMER_GROUP;
const storageAccountName = process.env.AZURE_STORAGE_ACCOUNT_NAME;
const containerName = process.env.AZURE_STORAGE_CONTAINER_NAME;


exports.handler = async function main() {

  // Get Access Keys from AWS Secret Manager
  let response;

  try {
    response = await secretsClient.send(
      new GetSecretValueCommand({
        SecretId: secretName,
        VersionStage: "AWSCURRENT" // VersionStage defaults to AWSCURRENT if unspecified.
      })
    )
  }
  catch (error) {
    throw error;
  }

  const secretJson = JSON.parse(response.SecretString);
  const eventHubAccessKey = secretJson['azureeventhubaccesskey'];
  const storageAccountAccessKey = secretJson['azurestorageaccountaccesskey'];

  // Construct the connection string for the Event Hubs and the Storage Account.
  const connectionString = "Endpoint=sb://"+eventHubNamespace+".servicebus.windows.net/;SharedAccessKeyName="+eventHubSharedAccessPolicyName+";SharedAccessKey="+eventHubAccessKey+";EntityPath="+eventHubName;
  const storageConnectionString = "DefaultEndpointsProtocol=https;AccountName="+storageAccountName+";AccountKey="+storageAccountAccessKey+";EndpointSuffix=core.windows.net";

  // Create a blob container client and a blob checkpoint store using the client.
  const containerClient = new ContainerClient(storageConnectionString, containerName);
  const checkpointStore = new BlobCheckpointStore(containerClient);

  // Create a consumer client for the event hub by specifying the checkpoint store.
  const consumerClient = new EventHubConsumerClient(consumerGroup, connectionString, eventHubName, checkpointStore);

  // Subscribe to the events, and specify handlers for processing the events and errors.
  const subscription = consumerClient.subscribe({
      processEvents: async (events, context) => {
        if (events.length === 0) {
          console.log(`No events received within wait time. Waiting for next interval`);
          return;
        }

        for (const event of events) {
          console.log(event.body);
          const params = {
            MessageBody: JSON.stringify(event.body),
            QueueUrl: sqsQueneName
          }
          await sqs.sendMessage(params).promise();
        }
        // Update the checkpoint.
        await context.updateCheckpoint(events[events.length - 1]);
      },

      processError: async (err, context) => {
        console.log(`Error : ${err}`);
      }
    },
    { startPosition: earliestEventPosition }
  );

  // After 60000 milliseconds, stop processing.
  await new Promise((resolve) => {
    setTimeout(async () => {
      await subscription.close();
      await consumerClient.close();
      resolve();
    }, 60000);
  });
}

