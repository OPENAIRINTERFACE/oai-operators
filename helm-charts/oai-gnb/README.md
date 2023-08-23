# Helm Chart for OAI Next Generation Node B (OAI-gNB)

This helm-chart is only tested for [RF Simulated oai-gnb](https://gitlab.eurecom.fr/oai/openairinterface5g/-/blob/develop/radio/rfsimulator/README.md). Though it is designed to work with split 8 radio units or USRPs. You can define dedicated interfaces for fronthaul, N2 and N3. In `template/deployment.yaml` there is a section to use it with USB based USRPs. The option to use RFSIM, USRPs or Radio Units is decided via configuration file. The container image always remains the same. 

We are in the process of testing the helm-chart with different USRPs, Radio Units and extend it for O-RAN 7.2 interface. We have already implemented 7.2 interface in OAI codebase.

Before using this helm-chart we recommend you read about OAI codebase and its working from the documents listed on [OAI gitlab](https://gitlab.eurecom.fr/oai/openairinterface5g/-/tree/develop/doc)

**Note**: This chart is tested on [Minikube](https://minikube.sigs.k8s.io/docs/) and [Red Hat Openshift](https://www.redhat.com/fr/technologies/cloud-computing/openshift) 4.10 and 4.12. RFSIM-GNB requires minimum 2CPU and 2Gi RAM and [multus-cni](https://github.com/k8snetworkplumbingwg/multus-cni) plugin for multiple interfaces. 

All the extra interfaces/multus interfaces created inside the pod are using `macvlan` mode. If your environment does not allow using `macvlan` then you need to change the multus definations. 

## Introduction

To know more about the feature set of OpenAirInterface you can check it [here](https://gitlab.eurecom.fr/oai/openairinterface5g/-/blob/develop/doc/FEATURE_SET.md#openairinterface-5g-nr-feature-set). 

The [codebase](https://gitlab.eurecom.fr/oai/openairinterface5g/-/tree/develop) for gNB, CU, DU, CU-CP/CU-UP, NR-UE is the same. Everyweek on [docker-hub](https://hub.docker.com/r/oaisoftwarealliance/oai-gnb) our [Jenkins Platform](https://jenkins-oai.eurecom.fr/view/RAN/) publishes two docker-images 

1. `oaisoftwarealliance/oai-gnb` for monolithic gNB, DU, CU, CU-CP 
2. `oaisoftwarealliance/oai-nr-cuup` for CU-UP. 

Each image has develop tag and a dedicated week tag for example `2023.w18`. We only publish Ubuntu 18.04/20.04 images. We do not publish RedHat/UBI images. These images you have to build from the source code on your RedHat systems or Openshift Platform. You can follow this [tutorial](../../../openshift/README.md) for that.

The helm chart of OAI-GNB creates multiples Kubernetes resources,

1. Service
2. Role Base Access Control (RBAC) (role and role bindings)
3. Deployment
4. Configmap
5. Service account
6. Network-attachment-defination (Optional only when multus is used)

The directory structure

```
.
├── Chart.yaml
├── templates
│   ├── configmap.yaml
│   ├── deployment.yaml
│   ├── _helpers.tpl
│   ├── multus.yaml
│   ├── NOTES.txt
│   ├── rbac.yaml
│   ├── serviceaccount.yaml
│   └── service.yaml
└── values.yaml
```

## Parameters

[Values.yaml](./values.yaml) contains all the configurable parameters. Below table defines the configurable parameters. You need a dedicated interface for Fronthaul. Creating deadicated interfaces for N2 and N3 is optional. You can use a single interface for N2 and N3.



|Parameter                       |Allowed Values                 |Remark                                          |
|--------------------------------|-------------------------------|------------------------------------------------|
|kubernetesType                  |Vanilla/Openshift              |Vanilla Kubernetes or Openshift                 |
|nfimage.repository              |Image Name                     |                                                |
|nfimage.version                 |Image tag                      |                                                |
|nfimage.pullPolicy              |IfNotPresent or Never or Always|                                                |
|imagePullSecrets.name           |String                         |Good to use for docker hub                      |
|serviceAccount.create           |true/false                     |                                                |
|serviceAccount.annotations      |String                         |                                                |
|serviceAccount.name             |String                         |                                                |
|podSecurityContext.runAsUser    |Integer (0,65534)              |                                                |
|podSecurityContext.runAsGroup   |Integer (0,65534)              |                                                |
|multus.defaultGateway           |Ip-Address                     |default route in the pod                        |
|multus.n2Interface.create       |true/false                     |                                                |
|multus.n2Interface.IPadd        |Ip-Address                     |                                                |
|multus.n2Interface.Netmask      |Netmask                        |                                                |
|multus.n2Interface.Gateway      |Ip-Address                     |                                                |
|multus.n2Interface.hostInterface|host interface                 |Host interface of the machine where pod will run|
|multus.n2Interface.routes       |Json                           |Routes you want to add in the pod               |
|multus.n3Interface.create       |true/false                     |                                                |
|multus.n3Interface.IPadd        |Ip-Address)                    |                                                |
|multus.n3Interface.Netmask      |Netmask                        |                                                |
|multus.n3Interface.Gateway      |Ip-Address                     |                                                |
|multus.n3Interface.hostInterface|host interface                 |Host interface of the machine where pod will run|
|multus.n3Interface.routes       |Json                           |Routes you want to add in the pod               |
|multus.ruInterface.create       |true/false                     |                                                |
|multus.ruInterface.IPadd        |Ip-Address                     |                                                |
|multus.ruInterface.Netmask      |Netmask                        |                                                |
|multus.ruInterface.Gateway      |Ip-Address                     |                                                |
|multus.ruInterface.hostInterface|host interface                 |Host interface of the machine where pod will run|
|multus.ruInterface.mtu          |Integer                        |Range [0, Parent interface MTU]                 |

The config parameters mentioned in `config` block of `values.yaml` are limited on purpose to maintain simplicity. They do not allow changing a lot of parameters of oai-gnb. If you want to use your own configuration file for oai-gnb. It is recommended to copy it in `templates/configmap.yaml` and set `config.mountConfig` as `true`. The command line for gnb is provided in `config.useAdditionalOptions`.

The charts are configured to be used with primary CNI of Kubernetes. When you will mount the configuration file you have to define static ip-addresses for N2, N3 and RU. Most of the primary CNIs do not allow static ip-address allocation. To overcome this we are using multus-cni with static ip-address allocation. At minimum you have to create one multus interface which you can use for N2, N3 and RU. If you want you can create dedicated interfaces.

You can find [here](https://gitlab.eurecom.fr/oai/openairinterface5g/-/tree/develop/targets/PROJECTS/GENERIC-NR-5GC/CONF) different sample configuration files for different bandwidths and frequencies. The binary of oai-gnb is called as `nr-softmodem`. To know more about its functioning and command line parameters you can visit this [page](https://gitlab.eurecom.fr/oai/openairinterface5g/-/blob/develop/doc/RUNMODEM.md)

## Advanced Debugging Parameters

Only needed if you are doing advanced debugging

|Parameter                        |Allowed Values                 |Remark                                        |
|---------------------------------|-------------------------------|----------------------------------------------|
|start.gnb                        |true/false                     |If true gnb container will go in sleep mode   |
|start.tcpdump                    |true/false                     |If true tcpdump container will go in sleepmode|
|includeTcpDumpContainer          |true/false                     |If false no tcpdump container will be there   |
|tcpdumpimage.repository          |Image Name                     |                                              |
|tcpdumpimage.version             |Image tag                      |                                              |
|tcpdumpimage.pullPolicy          |IfNotPresent or Never or Always|                                              |
|persistent.sharedvolume          |true/false                     |Save the pcaps in a shared volume with NRF    |
|resources.define                 |true/false                     |                                              |
|resources.limits.tcpdump.cpu     |string                         |Unit m for milicpu or cpu                     |
|resources.limits.tcpdump.memory  |string                         |Unit Mi/Gi/MB/GB                              |
|resources.limits.nf.cpu          |string                         |Unit m for milicpu or cpu                     |
|resources.limits.nf.memory       |string                         |Unit Mi/Gi/MB/GB                              |
|resources.requests.tcpdump.cpu   |string                         |Unit m for milicpu or cpu                     |
|resources.requests.tcpdump.memory|string                         |Unit Mi/Gi/MB/GB                              |
|resources.requests.nf.cpu        |string                         |Unit m for milicpu or cpu                     |
|resources.requests.nf.memory     |string                         |Unit Mi/Gi/MB/GB                              |
|readinessProbe                   |true/false                     |default true                                  |
|livenessProbe                    |true/false                     |default false                                 |
|terminationGracePeriodSeconds    |5                              |In seconds (default 5)                        |
|nodeSelector                     |Node label                     |                                              |
|nodeName                         |Node Name                      |                                              |

## How to use

0. Make sure the core network is running else you need to first start the core network. You can follow any of the below links
  - [OAI 5G Core Basic](../../oai-5g-basic/README.md)
  - [OAI 5G Core Mini](../../oai-5g-mini/README.md)

1. If you want to mount your configuration file then you set can `config.mountConfig`. The configuration file should be added in `templates/configmap.yaml`. Once the GNB is configured. 

```bash
helm install oai-gnb .
```

2. Configure the `oai-nr-ue` charts for `oai-gnb`, change `config.rfSimulator` to `oai-gnb` and `useAdditionalOptions` to "--sa -E --rfsim -r 106 --numerology 1 -C 3319680000 --nokrnmod --log_config.global_log_options level,nocolor,time". As the configuration of cu/du is set at this frequency and resource block. If you mount your own configuration file then set the configuration of nr-ue accordingly. 

```bash
helm install oai-nr-ue ../oai-nr-ue
```

3. Once NR-UE is connected you can go inside the pod and ping via `oai` interface. If you do not see this interface then the UE is not connected to gNB or have some issues at core network.

```bash
kubectl exec -it <oai-nr-ue-pod-name> -- bash
#ping towards spgwu/upf
ping -I oaitun_ue1 12.1.1.1
#ping towards google dns
ping -I oaitun_ue1 8.8.8.8
```

## Note

1. If you are using multus then make sure it is properly configured and if you don't have a gateway for your multus interface then avoid using gateway and defaultGateway parameter. Either comment them or leave them empty. Wrong gateway configuration can create issues with pod networking and pod will not be able to resolve service names.