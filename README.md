# Python web service to deploy QuestDB on Kubernetes

## Requirements

Tested on a Digital Ocean droplet running Ubuntu 20.04 and python 3.8 (should work fine elsewhere tho). Requires:

* [docker](https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-on-ubuntu-20-04)
* [minikube](https://minikube.sigs.k8s.io/docs/start/)
* add QuestDB image to docker `docker pull questdb/questdb`
* pip (if it's not on the host already)

If MiniKube is up you should get something like:

```
$ minikube kubectl get all
NAME                 TYPE        CLUSTER-IP   EXTERNAL-IP   PORT(S)   AGE
service/kubernetes   ClusterIP   10.96.0.1    <none>        443/TCP   16s
```

## Run

Pull down code:

```
pull down github repo
```

Install with python deps.  Since I'm on a throwaway droplet I just install globally, but use a venv if prefered (If you're installing to local might need to be careful it's on $PATH for uvicorn)

```
cd deployqdb
pip install .
```

Background a proxy into kubectl.  I considered setting up the whole project in a container, but authentication and opening ports gets a little messy.  Seems more straight forward for a throwaway project to have a proxy to a local port and avoid all that.

```
minikube kubectl -- proxy --port=8888 &
```

Run the simple webserver:

```
uvicorn deployqdb.api:app
```

Runs on 8000 by default.  Documentation at /docs.  After you run create you'll get a name, run status for this name and it'll return a QuestDB ip:port accessible from localhost

## Tests

The tests I've added are really integration tests rather than unit tests: they test interactions with k8s so can't be run in isolation, they require minikube to be available.  The 3 methods are also quite tightly coupled so are tested togther.  I don't think unit tests would be of much value here. Tests can be run with the standard pytest runner:

```
pytest
```
