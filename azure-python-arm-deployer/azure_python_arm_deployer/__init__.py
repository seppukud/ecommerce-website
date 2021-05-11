import datetime
import json
import os
import random

import pkg_resources
from azure.identity import ClientSecretCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.resource.resources.models import Deployment, DeploymentMode

TEMPLATE_PATH = "templates/{template_name}/azuredeploy.json"
PARAMETER_FILE_PATH = "templates/{template_name}/azuredeploy.parameters.json"

class ArmTemplateDeployer:
    """Deployer class to be initialized with subscription_id, resource_group_name,
    resource_group_location
    """
    def __init__(self, subscription_id, resource_group_name, resource_group_location):
        """Initializes ArmDeployerClass for consuming ARM templates

        :param subscription_id: Subscription ID
        :type subscription_id: str
        :param resource_group_name: Resource Group name to be created or updated
        :type resource_group: str
        :param resource_group_location: Resource Group location
        :type resource_group: str
        """
        self.subscription_id = os.environ.get(
            'AZURE_SUBSCRIPTION_ID', subscription_id)
        self.resource_group_name = resource_group_name
        self.resource_group_location = resource_group_location
        self.__credentials = ClientSecretCredential(
            client_id=os.environ['AZURE_CLIENT_ID'],
            client_secret=os.environ['AZURE_CLIENT_SECRET'],
            tenant_id=os.environ['AZURE_TENANT_ID']
        )

        self.client = ResourceManagementClient(
            self.__credentials, self.subscription_id)
        self.last_deployment_id = None

    def deploy(self, template_name, deployment_mode = DeploymentMode.INCREMENTAL):
        # Create or Update resource group before Deploying template
        self.client.resource_groups.create_or_update(
            self.resource_group_name,
            dict(
                location=self.resource_group_location
            )
        )

        # build template and parameters as json
        template_path = pkg_resources.resource_filename(
            "azure_arm_deployer", TEMPLATE_PATH.format(template_name=template_name))
        with open(template_path, "r") as template_file_fd:
            template = json.load(template_file_fd)

        parameter_path = pkg_resources.resource_filename(
            "azure_arm_deployer", PARAMETER_FILE_PATH.format(template_name=template_name))
        with open(parameter_path, "r") as parameter_path_fd:
            parameters = json.load(parameter_path_fd)["parameters"]

        deployment_properties = {
                'mode': deployment_mode,
                'template': template,
                'parameters': parameters
            }

        # create deployment name dynamically.
        self.last_deployment_id = f'{template_name}-{datetime.datetime.now().strftime("%m%d%Y")}-{random.getrandbits(32)}'

        # returns LROPoller of type 
        # https://docs.microsoft.com/en-us/python/api/msrest/msrest.polling.lropoller?view=azure-python
        deployment_async_operation = self.client.deployments.begin_create_or_update(
            self.resource_group_name,
            f"{template_name}-deployment",
            Deployment(properties=deployment_properties)
        )

        # wait for default time to let the async deployment operation complete.
        deployment_async_operation.wait()
        if not deployment_async_operation.done:
            raise Exception("Deployment not complete after wait period also.")

        # return result as operation complete
        return deployment_async_operation.result

    def delete(self, deployment_name = None):
        if not deployment_name:
            deployment_name = self.last_deployment_id
        if not deployment_name:
            raise Exception("Mandatory to give deployment name/id, either during init object or while calling delete method")
        deployment_async_operation = self.client.deployments.begin_delete(
            self.resource_group_name,
            deployment_name
        )

        # wait for default time to let the async deletion operation complete.
        deployment_async_operation.wait()
        if not deployment_async_operation.done:
            raise Exception("Deletion not complete after wait period also.")

        # return result as operation complete
        return deployment_async_operation.result
