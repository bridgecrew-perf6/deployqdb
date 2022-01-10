import os
import uuid
import yaml

import kubernetes.client
import requests
from fastapi import FastAPI, HTTPException
from typing import Optional
from pydantic import BaseModel, Field

# NOTE This is not ideal, but seems to be the only way to grab the minikube ip to access QuestDB instances outside the cluster
MINIKUBE_IP = os.popen("minikube ip").read()[:-1]
K8S_CONFIG = kubernetes.client.Configuration()
K8S_CONFIG.host = "http://127.0.0.1:8888" # NOTE hardcoding the local proxy port, see README for more
MANIFESTS = [
    {
        "manifest_file": "deployment.yaml",
        "api": kubernetes.client.AppsV1Api,
        "method": "create_namespaced_deployment",
        "delete_method": "delete_namespaced_deployment"
    },
    {
        "manifest_file": "service.yaml",
        "api": kubernetes.client.CoreV1Api,
        "method": "create_namespaced_service",
        "delete_method": "delete_namespaced_service"
    },
]

description = """
Simple Python web service that allows you to interact with the Kubernetes API 
to create, check the status of, and delete QuestDB instances.
"""
tags_metadata = [
    {
        "name": "create",
        "description": "Creates a deployment with a single QuestDB pod, and a service to allow for external access via a dynamically assigned nodePort",
    },
    {
        "name": "status",
        "description": "Checks the k8s deployment condition, external address and status code returned by the QuestDB instance",
    },
    {
        "name": "delete",
        "description": "Deletes the deployment and service associated with this name",
    },
]
app = FastAPI(
        title="deployqdb",
        description=description,
        openapi_tags=tags_metadata
        )


# Data models/schemas
class NewDB(BaseModel):
    # NOTE These are just placeholders that don't do anything
    # but this is where you could add user specified options
    description: Optional[str] = None
    instance_size: Optional[str] = None

class DB(NewDB):
    name: str = Field(...,description="Unique identifier for the QuestDB instance")

class DBStatus(BaseModel):
    questdb_address: str = Field(...,description="Address at which to access QuestDB instance")
    questdb_status_code: int = Field(...,description="Status code returned by pinging questdb_address (0 indicates no response)")
    deployment_condition: list # NOTE I imagine you'd want to think carefully about exactly what information to surface to users, but this seems like some easy context for now


@app.post("/deployqdb", tags=["create"], response_model=DB)
def create(newdb: Optional[NewDB] = None):
    """Create a QuestDB instance"""
    name = 'questdb-' + str(uuid.uuid4()) # chance of name clash is astronomical
    for manifest in MANIFESTS:
        response = apply_manifest(name=name,**manifest)
        if 'error' in response:
            raise HTTPException(status_code=404, detail=response['error'])
    if newdb:
        return DB(**newdb.dict(),name=name)
    return DB(name=name)


def apply_manifest(manifest_file, api, method, delete_method, name):
    """Utility function to apply k8s manifests"""
    with open(os.path.join(os.path.dirname(__file__), manifest_file)) as f:
        body = yaml.safe_load(f)
        body['metadata']['name'] = name
    response = kubernetes_api(api=api,
                              method=method,
                              arguments={'namespace':'default', 'body':body})
    return response


@app.get("/deployqdb/{name}", tags=["status"], response_model=DBStatus)
def status(name):
    """Check the status of a QuestDB instance"""
    response = kubernetes_api(api=kubernetes.client.AppsV1Api,
                              method='list_namespaced_deployment',
                              arguments={'namespace':'default', 'field_selector':'metadata.name='+name})
    if 0 == len(response['items']):
        raise HTTPException(status_code=404, detail="Item not found")
    deployment_condition = response['items'][0]['status']['conditions']

    response = kubernetes_api(api=kubernetes.client.CoreV1Api,
                              method='list_namespaced_service',
                              arguments={'namespace':'default', 'field_selector':'metadata.name='+name})
    questdb_address = 'http://{}:{}'.format(MINIKUBE_IP,response['items'][0]['spec']['ports'][0]['node_port'])

    try:
        resp = requests.get(questdb_address)
        status_code = resp.status_code
    except:
        status_code = 0

    return DBStatus(questdb_address=questdb_address,
                    questdb_status_code=status_code,
                    deployment_condition=deployment_condition)


@app.delete("/deployqdb/{name}", tags=["delete"])
def delete(name):
    """Delete a QuestDB instance

    Deletes the deployment and service associated with this name
    """
    for manifest in MANIFESTS:
        response = kubernetes_api(api=manifest['api'],
                                  method=manifest['delete_method'],
                                  arguments={'namespace':'default', 'name':name})
        if 'error' in response:
            raise HTTPException(status_code=404, detail="Item not found")
    return {'status':'deleted'}


def kubernetes_api(api, method, arguments):
    """Utility function to wrap calls to the k8s API"""
    with kubernetes.client.ApiClient(K8S_CONFIG) as api_client:
        api_instance = api(api_client)
        try:
            response = getattr(api_instance, method)(**arguments)
            return response.to_dict()
        except kubernetes.client.rest.ApiException as e:
            return {'error': "ApiException when calling {}->{}: {}\n".format(api.__name__,method,e)}
        except TypeError as e:
            return {'error': "TypeException when calling {}->{}: {}\n".format(api.__name__,method,e)}
