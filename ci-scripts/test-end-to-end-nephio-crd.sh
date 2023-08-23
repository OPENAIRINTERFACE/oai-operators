#/bin/bash
# set -eo pipefail
TAG=$1
PARENT=$2

## Testing only operators without nephio
./create-cluster.sh
#build inside minikube directly
eval $(minikube -p minikube docker-env)
./build-images.sh $TAG $PARENT
fetch the crds from nephio repository
./getcrd.sh
#define crds
kubectl create -f ../crd/
#create ns for controllers
kubectl create ns oaiops
#create ns for nfs
kubectl create ns oainfs
#deploy controllers
kubectl create -f ../oai5gcore/controllerdeploy/ -n oaiops
#Wait for all the controllers
sleep 5
kubectl wait --for=condition=ready pod -n oaiops -l app.kubernetes.io/name=oai-amf-controller
kubectl wait --for=condition=ready pod -n oaiops -l app.kubernetes.io/name=oai-smf-controller
kubectl wait --for=condition=ready pod -n oaiops -l app.kubernetes.io/name=oai-nrf-controller
kubectl wait --for=condition=ready pod -n oaiops -l app.kubernetes.io/name=oai-upf-controller
kubectl wait --for=condition=ready pod -n oaiops -l app.kubernetes.io/name=oai-udr-controller
kubectl wait --for=condition=ready pod -n oaiops -l app.kubernetes.io/name=oai-udm-controller
kubectl wait --for=condition=ready pod -n oaiops -l app.kubernetes.io/name=oai-ausf-controller
#deploy mysql
helm install -n oainfs mysql ../helm-charts/mysql/
sleep 2
kubectl wait --for=condition=ready pod -n oainfs -l app=mysql
#create nads
kubectl create -f ../oai5gcore/nad -n oainfs
## Deploy the network functions
kubectl create -f ../oai5gcore/nfdeploy -n oainfs
sleep 5
kubectl wait --for=condition=ready pod -n oainfs -l workload.nephio.org/oai=amf
kubectl wait --for=condition=ready pod -n oainfs -l workload.nephio.org/oai=smf
kubectl wait --for=condition=ready pod -n oainfs -l workload.nephio.org/oai=nrf
kubectl wait --for=condition=ready pod -n oainfs -l workload.nephio.org/oai=upf
kubectl wait --for=condition=ready pod -n oainfs -l workload.nephio.org/oai=udr
kubectl wait --for=condition=ready pod -n oainfs -l workload.nephio.org/oai=udm
kubectl wait --for=condition=ready pod -n oainfs -l workload.nephio.org/oai=ausf