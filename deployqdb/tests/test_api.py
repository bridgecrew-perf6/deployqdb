import pytest
import time

import kubernetes
from fastapi.testclient import TestClient

from deployqdb import app, kubernetes_api, delete


client = TestClient(app)


@pytest.fixture(scope='function')
def kube():
    # This fixture doesn't do any real setup, I'm just using it to cleanup consistently after tests
    # It finds any leftover services and deployments, and deletes them after testing
    yield None
    response = kubernetes_api(api=kubernetes.client.AppsV1Api,
                              method='list_namespaced_deployment',
                              arguments={'namespace':'default'})
    for name in [item['metadata']['name'] for item in response['items']]:
        delete(name=name)


def test_creation(kube):
    response = client.post("/deployqdb") # Test creation endpoint works
    assert response.status_code == 200
    assert response.json()['name'].startswith('questdb-') # and returns a name


def test_deletion(kube):
    name = client.post("/deployqdb").json()['name']
    response = client.delete("/deployqdb/"+name)
    assert response.status_code == 200
    assert response.json()['status'] == 'deleted' # check the deletion endpoint works
    response = client.delete("/deployqdb/"+name)
    assert response.status_code == 404


def test_status(kube):
    response = client.get("/deployqdb/questdb-fake") # try getting status for an instnace that doesn't exist
    assert response.status_code == 404
    name = client.post("/deployqdb").json()['name']
    time.sleep(10) # NOTE This is not ideal, but need a short pause to allow the instance to spin up
    response = client.get("/deployqdb/"+name) # and then check status for one that does
    assert response.status_code == 200
    assert response.json()['questdb_status_code'] == 200 # QuestDB instance should now be responsive
