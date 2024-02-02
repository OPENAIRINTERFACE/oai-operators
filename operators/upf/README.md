<table style="border-collapse: collapse; border: none;">
  <tr style="border-collapse: collapse; border: none;">
    <td style="border-collapse: collapse; border: none;">
      <a href="http://www.openairinterface.org/">
         <img src="../../docs/images/oai_final_logo.png" alt="" border=3 height=50 width=150>
         </img>
      </a>
    </td>
    <td style="border-collapse: collapse; border: none; vertical-align: center;">
      <b><font size = "5">OpenAirInterface UPF Operator</font></b>
    </td>
  </tr>
</table>

The operator is designed using [kopf](https://kopf.readthedocs.io/). The operator is completely written in python. At the moment the operator is highly experimental and designed for orchestration via [nephio](https://nephio.org/). 

It can be used for `oai-upf` version `develop`.

**NOTE**: So far we have only tested the operator on a minikube cluster. 

The directory structure is below:

```bash
.
├── controllers
│   ├── controller.py (Main controller logic)
│   └── utils.py (Supporting functions)
├── deployment
│   └── upf.yaml (to deploy the operator)
├── Dockerfile  
├── package
│   └── upfdeploy.yaml (Standalone deployment of UPF operator)
├── README.md
└── requirements.txt (All the needed python dependencies)
```

## Functioning

The controller is listening to nephio proposed crd `workload.nephio.org_upfdeployments.yaml` cluster wide. In the future it will listen to OAI proposed CRDs also.

Controller requires configuration file of the network function and it allows configuring certain config parameters when the controller is deployed. The controller requires two configmaps when running inside a pod or during development phase you can just provide the path of the network function configuration file and the controllers configuration file. The reason of having controllers configuration file is to only expose some important paramters to configure the network function rather than exposing all the parameters. 

The idea of this controller is not to expose multiple configuration paramters but to easily deploy the network function with less efforts from the user. 

There are some environment parameters which are used by the controller to configure network function configuration files. They are present in [utils.py](controllers/utils.py)

```bash
HTTPS_VERIFY = bool(os.getenv('HTTPS_VERIFY',False)) ## To verfiy HTTPs certificates when communicating with cluster
TOKEN=os.popen('cat /var/run/secrets/kubernetes.io/serviceaccount/token').read() ## Token used to communicate with Kube cluster
NF_TYPE=str(os.getenv('NF_TYPE','upf'))      ## Network function name
LABEL={'workload.nephio.org/oai': f"{NF_TYPE}"}   ## Labels to put inside the owned resources
OP_CONF_PATH=str(os.getenv('OP_CONF_PATH',f"/tmp/op/{NF_TYPE}.yaml"))  ## Operators configuration file
NF_CONF_PATH = str(os.getenv('NF_CONF_PATH',f"/tmp/nf/{NF_TYPE}.conf"))  ## Network function configuration file
DEPLOYMENT_FETCH_INTERVAL=int(os.getenv('DEPLOYMENT_FETCH_INTERVAL',1)) # Fetch the status of deployment every x seconds
DEPLOYMENT_FETCH_ITERATIONS=int(os.getenv('DEPLOYMENT_FETCH_ITERATIONS',100))  # Number of times to fetch the deployment
LOG_LEVEL = str(os.getenv('LOG_LEVEL','INFO'))    ## Log level of the controller
TESTING = bool(os.getenv('TESTING','no'))    ## If testing the network function, it will remove the init container which checks for NRFs availability
```

UPF needs network-attachement-defination for N2 interface. Normally its nephio which will provide the nad. Controller is also capable of creating a nad via changing these fields in deployment/upf.yaml configmap of upf.yaml

```bash
    nad:
      parent: 'eth1'   #parent interface on the host machine to create the bridge
      create: False    #If false it will wait for multus defination in the cluster namespace
``` 

In case of docker pull limit on your network better to use pull secrets, just authenticated with the docker hub. You can add the pull secret in the operator configuration, upf.yaml in configmap like below

```bash
    imagePullSecrets:
      - name: test
```

## Deployment

The image is still not hosted on public respositories so you have to create an image

```bash
docker build -f Dockerfile -t oai-upf-controller:develop . --no-cache
```

Create the CRD

```bash
kubectl create -f ../../crd/workload.nephio.org_nfdeployments.yaml
```

Start the controller 

```bash
kubectl create -f deployment/upf.yaml
```

Normally nephio will create the nad incase you want to create manually then you do 

```bash
kubectl create -f ../../oai5gcore/nad/upf.yaml
```

Create the resource

```bash
kubectl create -f package/upfdeploy.yaml
```

## Development environment

For development it is good to use virtual python environment, I am using `virtualenv`

``` bash
sudo apt install virtalenv
virtualenv -p python3 -m venv
```

Install the requirements

```
pip install -r requirements.txt
```

Make sure you copy operators `yaml` configuration file network functions `.conf` from `deployment/upf.yaml` and copy it to two different files and configure the env parameters 

```bash
export OP_CONF_PATH='/path-to/op/upf.yaml'
export NF_CONF_PATH='/path-to/nf/upf.conf'
```
Now start the operator

```bash
kopf run controllers/controller.py --verbose
```

## Note

In case you are not able to remove the package because the finalizer is blocking it then you can patch

```bash
kubectl patch nfdeployments.workload.nephio.org oai-upf -p '{"metadata": {"finalizers": []}}' --type merge
```