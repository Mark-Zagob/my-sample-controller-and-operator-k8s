import logging
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import socketio
import asyncio

# Logging setup
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Load Kubernetes configuration
config.load_incluster_config()
#config.load_kube_config()
# Create a Kubernetes API client
api_client = client.CustomObjectsApi()

class InforzResource:
    """Represents an InforZ custom resource in Kubernetes."""

    def __init__(self, name, namespace="dung-crds-test"):
        self.name = name
        self.namespace = namespace
        self.api_client = api_client

    async def update(self, data_value):
        """Updates or creates the InforZ resource."""
        inforz_obj = {
            "apiVersion": "vtdc.local/v1beta1",
            "kind": "InforZ",
            "metadata": {
                "name": self.name
            },
            "spec": {
                "data": data_value.get("value"),
                "personal": data_value.get("name"),
                "gitrepo": data_value.get("link-git")
            }
        }

        try:
            # Try to update the existing Inforz resource
            self.api_client.patch_namespaced_custom_object(
                group="vtdc.local",
                version="v1beta1",
                namespace=self.namespace,
                plural="informationz",
                name=self.name,
                body=inforz_obj
            )
            logger.info(f"InforZ custom resource '{self.name}' updated successfully!")

        except ApiException as e:
            if e.status == 404:  # Resource not found, create it
                try:
                    self.api_client.create_namespaced_custom_object(
                        group="vtdc.local",
                        version="v1beta1",
                        namespace=self.namespace,
                        plural="informationz",
                        body=inforz_obj
                    )
                    logger.info(f"InforZ custom resource '{self.name}' created successfully!")
                except ApiException as e:
                    logger.error(f"Error creating InforZ custom resource '{self.name}': {e}")
            else:
                logger.error(f"Error updating InforZ custom resource '{self.name}': {e}")

class ApiWatcher:
    """Watches for API updates and updates the InforZ resource."""

    def __init__(self, url, inforz_name="my-inforz"):
        self.url = url
        self.inforz_resource = InforzResource(inforz_name)
        self.sio = socketio.AsyncClient()

        @self.sio.event
        async def process_handler(data):
            await self.process_data(data)

    async def start(self):
        await self.sio.connect(self.url,transports=['websocket'], namespaces=['/'])
        logger.info(f"Connected to API at {self.url} and listening event....")
        await self.sio.wait()

    async def process_data(self, data):
        logger.info("Inside process_data function")
        #use that instead of gitrepo = data['informations']['link-git']
        informations = data.get('informations', {})
        await self.inforz_resource.update(informations)
        logger.info(f"Value changed for InforZ resource '{self.inforz_resource.name}'")

if __name__ == '__main__':
    api_url = "http://flask-production:5000"
    watcher = ApiWatcher(api_url)
    asyncio.run(watcher.start())