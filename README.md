# Ingesting administrative logs from Microsoft Azure to AWS CloudTrail Lake

This project contains source code and supporting files for a serverless application that you can deploy with the SAM CLI.

## Deploy the SAM application

The Serverless Application Model Command Line Interface (SAM CLI) is an extension of the AWS CLI that adds functionality for building and testing Lambda applications. It uses Docker to run your functions in an Amazon Linux environment that matches Lambda. It can also emulate your application's build environment and API.

To use the SAM CLI, you need the following tools.

* SAM CLI - [Install the SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
* Node.js - [Install Node.js 18](https://nodejs.org/en/), including the NPM package management tool.
* Docker - [Install Docker community edition](https://hub.docker.com/search/?type=edition&offering=community)

To build and deploy your application for the first time, run the following in your shell:

```bash
sam build
sam deploy --guided
```

The first command will build the source of your application. The second command will package and deploy your application to AWS, with a series of prompts:

* **CloudTrailEventDataStoreArn (Optional)** - Arn of the event data store into which the Administrative Logs from Azure will be ingested. If no Arn is provided, a new event data store will be created.
* **CloudTrailEventRetentionPeriod** - The number of days to retain events ingested into CloudTrail. The minimum is 7 days and the maximum is 2,557 days. Defaults to 7 days.
* **AzureEventHubsNamespace** – The name of the namespace created on Azure Event Hubs.
* **AzureEventHubsName** – The name of the Event Hubs instance created in the namespace.
* **AzureEventHubsSharedAccessPolicyName** – The name of the shared access policy created within the Azure Event Hubs instance.
* **AzureEventHubsSharedAccessKey** – One of the available keys associated with the shared access policy. This parameter will stored on secrets manager.
* **AzureStorageAccountName** – The name of the Azure Storage account. This account needs to be publicly accessible.
* **AzureStorageContainerName** – The name of the Azure storage account container we created on step 1. This is used as the persistent store for maintaining checkpoints and partition ownership information while processing events from Azure Event Hubs.
* **AzureStorageAccountAccessKey** – Specify one of the available access keys on the Azure storage account.
* **UserType** - The value assigned to the userIdentity.type field for all events ingested into CloudTrail. Defaults to `MSAzureUser`.
* **Save arguments to samconfig.toml**: If set to yes, your choices will be saved to a configuration file inside the project, so that in the future you can just re-run `sam deploy` without parameters to deploy changes to your application.



## Cleanup

To delete the sample application that you created, use the AWS CLI. Assuming you used your project name for the stack name, you can run the following:

```bash
sam delete --stack-name aws-cloudtrail-lake-ingesting-azure-activity-logs
```

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.