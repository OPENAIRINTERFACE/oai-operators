<table style="border-collapse: collapse; border: none;">
  <tr style="border-collapse: collapse; border: none;">
    <td style="border-collapse: collapse; border: none;">
      <a href="http://www.openairinterface.org/">
         <img src="../../docs/images/oai_final_logo.png" alt="" border=3 height=50 width=150>
         </img>
      </a>
    </td>
    <td style="border-collapse: collapse; border: none; vertical-align: center;">
      <b><font size = "5">OpenAirInterface UDM Operator</font></b>
    </td>
  </tr>
</table>


The operator is designed using [kopf](https://kopf.readthedocs.io/). The operator is completely written in python. At the moment the operator is highly experimental and designed for orchestration via [nephio](https://nephio.org/). 

The directory structure is below:

```bash
.
├── controllers
│   ├── controller.py (Main controller logic)
│   └── utils.py (Supporting functions)
├── deployment
│   └── nf.yaml (to deploy the operator)
├── Dockerfile  
├── package
│   └── deploy.yaml (Standalone deployment of UDM operator)
├── README.md
└── requirements.txt (All the needed python dependencies)
```

## Functioning

**NOTE**: The controller is listening to nephio proposed crd `workload.nephio.org_nfdeployments.yaml` cluster wide. 

Controller requires configuration file of the network function and it allows configuring certain config parameters when the controller is deployed. The controller requires two configmaps when running inside a pod or during development phase you can just provide the path of the network function configuration file and the controllers configuration file. The reason of having controllers configuration file is to only expose some important paramters to configure the network function rather than exposing all the parameters. 

The idea of this controller is not to expose multiple configuration paramters but to easily deploy the network function with less efforts from the user. 

There are some environment parameters which are used by the controller to configure network function configuration files. They are present in [utils.py](controllers/utils.py)

```bash
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
KUBERNETES_TYPE=str(os.getenv('KUBERNETES_TYPE','vanilla')).lower()    ##Allowed values VANILLA/Openshift
if KUBERNETES_TYPE not in ['vanilla','openshift']:
    print('Allowed values for kubernetes type are vanilla/openshift')
NF_TYPE=str(os.getenv('NF_TYPE','udm'))      ## Network function name
LABEL={'workload.nephio.org/oai': f"{NF_TYPE}"}   ## Labels to put inside the owned resources
OP_CONF_PATH=str(os.getenv('OP_CONF_PATH',f"/tmp/op/{NF_TYPE}.yaml"))  ## Operators configuration file
NF_CONF_PATH = str(os.getenv('NF_CONF_PATH',f"/tmp/nf/{NF_TYPE}.yaml"))  ## Network function configuration file
DEPLOYMENT_FETCH_INTERVAL=int(os.getenv('DEPLOYMENT_FETCH_INTERVAL',1)) # Fetch the status of deployment every x seconds
DEPLOYMENT_FETCH_ITERATIONS=int(os.getenv('DEPLOYMENT_FETCH_ITERATIONS',100))  # Number of times to fetch the deployment
LOG_LEVEL = str(os.getenv('LOG_LEVEL','INFO'))    ## Log level of the controller
TESTING = str(os.getenv('TESTING','yes'))    ## If testing the network function, it will remove the init container which checks for NRFs availability
HTTPS_VERIFY = bool(os.getenv('HTTPS_VERIFY',False)) ## To verfiy HTTPs certificates when communicating with cluster
TOKEN=os.popen('cat /var/run/secrets/kubernetes.io/serviceaccount/token').read() ## Token used to communicate with Kube cluster
KUBERNETES_BASE_URL = str(os.getenv('KUBERNETES_BASE_URL','http://127.0.0.1:8080'))
```

In case of docker pull limit on your network better to use pull secrets, just authenticated with the docker hub. You can add the pull secret in the operator configuration, nf.yaml in configmap like below

```bash
    imagePullSecrets:
      - name: test
```

**NOTE**: All the network function controllers except upf and nrf have the same functioning. Though they have a seperate code base but its still similar at the moment.

## Deployment

The image is hosted on public respositories, but if you made changes then you need to built it:

```bash
docker build -f Dockerfile -t oai-udm-controller:develop. --no-cache
```

Create the CRD

```bash
kubectl create -f ../../crd/workload.nephio.org_nfdeployments.yaml
```

Start the controller 

```bash
kubectl create -f deployment/nf.yaml
```

Create the resource

```bash
kubectl create -f package/deploy.yaml
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

Make sure you copy operators `yaml` configuration file and network functions `yaml` configuration file from `deployment/udm.yaml` to two different files respectively and configure the env parameters:  

```bash
export OP_CONF_PATH='/path-to/op/udm.yaml'
export NF_CONF_PATH='/path-to/nf/udm.conf'
```
Now start the operator

```bash
kopf run controllers/controller.py --verbose
```

## Note

In case you are not able to remove the package because the finalizer is blocking it then you can patch

```bash
kubectl patch nfdeployments.workload.nephio.org oai-udm -p '{"metadata": {"finalizers": []}}' --type merge
```