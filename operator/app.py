import kopf
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import os,git,shutil, logging,yaml,datetime
from jinja2 import Template
import asyncio
import aiofiles

#define kubernetes configuration
config.load_incluster_config()
#config.load_kube_config()
api_client = client.CustomObjectsApi()
corev1 = client.CoreV1Api()
appv1 = client.AppsV1Api()

#logging
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


async def load_data(spec,name,cmname,deployname):
    #get values from spec
    data = str(spec.get('data'))
    personal = spec.get('personal')
    link = spec.get('gitrepo')
    
    #clone repo
    logger.info("repo cloned")
    shutil.rmtree('./repoz', ignore_errors=True)
    os.makedirs(name='./repoz',mode=655,exist_ok=True)
    await asyncio.to_thread(git.Repo.clone_from,link,'./repoz', branch='template')
    
    #get list of files
    filez = os.listdir('./repoz/')
    logger.info(f"list files {filez}")
    
    #generate index.html from template
    async with aiofiles.open(f'./repoz/config-file/index.html', 'r') as f:
        file_content = await f.read()
    configmap_data = Template(file_content).render(name=personal, data=data)
    logger.info(f"configmap_data: {configmap_data}")
    
    #generate deployment file from template
    async with aiofiles.open(f'./repoz/yaml-files/deployment.yaml', 'r') as f:
        file_content = await f.read()
    deployment_file = Template(file_content).render(name=deployname,cmname=cmname)
    deployment_file = yaml.safe_load(deployment_file)
    logger.info(f"deployment_file: {deployment_file}")
    
    #define body of config map
    configmap_body = client.V1ConfigMap(
        api_version = "v1",
        kind = "ConfigMap",
        metadata = client.V1ObjectMeta(
            name = f'{name}-configmap'
        ),
        data = {
            'data': configmap_data
        }
    )
    return configmap_body, deployment_file


async def restart_deployment(deployment, namespace):
    now = datetime.datetime.utcnow()
    now = str(now.isoformat("T") + "Z")
    body = {
        'spec': {
            'template':{
                'metadata': {
                    'annotations': {
                        'kubectl.kubernetes.io/restartedAt': now
                    }
                }
            }
        }
    }
    try:
        await asyncio.to_thread(appv1.patch_namespaced_deployment,deployment, namespace, body, pretty='true')
        logger.info(f"Deployment {deployment} RESTARTED in namespace {namespace}")
    except ApiException as e:
        logger.error(f"Exception when calling AppsV1Api->read_namespaced_deployment_status: {e}")

@kopf.on.event('vtdc.local', 'v1beta1', 'informationz')
async def on_handler(event,spec, name, namespace, **kwargs):
    #get values of configmap from repo
    #configmap_data, deployment_file = await load_data(spec,deployname=f'{name}-deployment',cmname=f'{name}-configmap')
    event_type = event['type']
    #create, update and delete configmap and deployment
    if event_type == 'ADDED':
        try:
            configmap_body, deployment_file = await load_data(spec,name,deployname=f'{name}-deployment',cmname=f'{name}-configmap')
            #create configmap
            await asyncio.to_thread(corev1.create_namespaced_config_map,
                namespace = namespace, 
                body  =  configmap_body
            )
            logger.info(f"ConfigMap {name}-configmap created in namespace '{namespace}'")
            #create deployment and map configmap to deployment
            await asyncio.to_thread(appv1.create_namespaced_deployment,
                namespace = namespace, 
                body  = deployment_file
                    
            )
            logger.info(f"Deployment {name}-deployment CREATED in namespace '{namespace}'")
        except ApiException as api_err:
            logger.error(f"Kubernetes API error: {api_err}")
        except Exception as err:
            logger.error(f"Create error: {err}")
        
    elif event_type == 'MODIFIED':        
        try:
            configmap_body, deployment_file = await load_data(spec,name,deployname=f'{name}-deployment',cmname=f'{name}-configmap')
            await asyncio.to_thread(corev1.patch_namespaced_config_map,
                name = f'{name}-configmap',
                namespace = namespace, 
                body  =  configmap_body
            )
            await restart_deployment(f'{name}-deployment', namespace)
            logger.info(f"ConfigMap '{name}' UPDATED in namespace '{namespace}'")
        except ApiException as api_err:
            logger.error(f"Kubernetes API error: {api_err}")
        except Exception as err:
            logger.error(f"modified error: {err}")
    elif event_type == 'DELETED':
        try:
            delete_options = client.V1DeleteOptions()
            await asyncio.to_thread(corev1.delete_namespaced_config_map, name=f'{name}-configmap', namespace=namespace, body=delete_options)
            await asyncio.to_thread(appv1.delete_namespaced_deployment, name=f'{name}-deployment', namespace=namespace, body=delete_options)
            logger.info(f"ConfigMap '{name}'-configmap and Deployment '{name}-deployment' DELETED in namespace '{namespace}'")
        except ApiException as api_err:
            logger.error(f"Kubernetes API error: {api_err}")
        except Exception as err:
            logger.error(f"delete error: {err}")