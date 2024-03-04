################################################################################
# Licensed to the OpenAirInterface (OAI) Software Alliance under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The OpenAirInterface Software Alliance licenses this file to You under
# the terms found in the LICENSE file in the root of this source tree.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#-------------------------------------------------------------------------------
# For more information about the OpenAirInterface (OAI) Software Alliance:
#      contact@openairinterface.org
##################################################################################

#/bin/bash
set -eo pipefail
## Usage ./ci-scripts/test-end-to-end.sh $tag $parent_repo $username_repositor $password_repository $kubernetes_type
TAG=$1
PARENT=$2
USER=$3
PASS=$4
KUBERNETES_TYPE=${$5:-'vanilla'} #vanilla or openshift

function cleanup {
  echo "Removing minikube"
  minikube delete
  sed -i 's/imagePullPolicy\: IfNotPresent/imagePullPolicy\: Always/g' oai5gcore/controllerdeploy/*
  sed -i 's/openshift/vanilla/g' oai5gcore/controllerdeploy/*
}

trap cleanup EXIT
## Testing only operators without nephio
echo "----------Test Started ----------"
## create infrastructure
./ci-scripts/create-cluster.sh
#Build inside minikube directly
eval $(minikube -p minikube docker-env)
./ci-scripts/build-images.sh $TAG $PARENT
## Use images from minikube ns 
sed -i 's/imagePullPolicy\: Always/imagePullPolicy\: IfNotPresent/g' oai5gcore/controllerdeploy/*
sed -i 's/vanilla/openshift/g' oai5gcore/controllerdeploy/*
#create ns for controllers
kubectl create ns oaiops
#create namespaces
kubectl create -f oai5gcore/nad/namespace.yaml
#create nad
kubectl create -f oai5gcore/nad/amf.yaml
kubectl create -f oai5gcore/nad/smf.yaml
kubectl create -f oai5gcore/nad/upf-edge.yaml
#deploy mysql
helm install -n oaicp mysql helm-charts/mysql/
sleep 2
kubectl wait --for=condition=ready pod -n oaicp -l app=mysql --timeout=3m
#deploy controllers
kubectl create -f oai5gcore/controllerdeploy/
#Wait for all the controllers
sleep 5
kubectl wait --for=condition=ready pod -n oaiops -l app.kubernetes.io/name=oai-amf --timeout=3m
kubectl wait --for=condition=ready pod -n oaiops -l app.kubernetes.io/name=oai-smf --timeout=3m
kubectl wait --for=condition=ready pod -n oaiops -l app.kubernetes.io/name=oai-nrf --timeout=3m
kubectl wait --for=condition=ready pod -n oaiops -l app.kubernetes.io/name=oai-upf --timeout=3m
kubectl wait --for=condition=ready pod -n oaiops -l app.kubernetes.io/name=oai-udr --timeout=3m
kubectl wait --for=condition=ready pod -n oaiops -l app.kubernetes.io/name=oai-udm --timeout=3m
kubectl wait --for=condition=ready pod -n oaiops -l app.kubernetes.io/name=oai-ausf --timeout=3m
## Deploy the network functions
kubectl create -f oai5gcore/nfdeploy/
sleep 10
kubectl wait --for=condition=ready pod -n oaicp -l workload.nephio.org/oai=amf --timeout=5m
kubectl wait --for=condition=ready pod -n oaicp -l workload.nephio.org/oai=smf --timeout=5m
kubectl wait --for=condition=ready pod -n oaicp -l workload.nephio.org/oai=nrf --timeout=5m
kubectl wait --for=condition=ready pod -n oai-upf -l workload.nephio.org/oai=upf --timeout=5m
kubectl wait --for=condition=ready pod -n oaicp -l workload.nephio.org/oai=udr --timeout=5m
kubectl wait --for=condition=ready pod -n oaicp -l workload.nephio.org/oai=udm --timeout=5m
kubectl wait --for=condition=ready pod -n oaicp -l workload.nephio.org/oai=ausf --timeout=5m
## Deploy gNB
helm install gnb helm-charts/oai-gnb
sleep 10
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=oai-gnb --timeout=5m
## Deploy NR-UE
helm install nrue helm-charts/oai-nr-ue
sleep 10
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=oai-nr-ue --timeout=5m
sleep 20
## Check if the UE connects via looking at tunnel interface
kubectl exec -it $(kubectl get pods  -l app.kubernetes.io/name=oai-nr-ue | grep nr-ue | awk '{print $1}') -- ifconfig oaitun_ue1
kubectl exec -it $(kubectl get pods  -l app.kubernetes.io/name=oai-nr-ue | grep nr-ue | awk '{print $1}') -- ping -I oaitun_ue1 10.1.0.1 -c 4
## Clean up
sed -i 's/imagePullPolicy\: IfNotPresent/imagePullPolicy\: Always/g' oai5gcore/controllerdeploy/*
sed -i 's/openshift/vanilla/g' oai5gcore/controllerdeploy/*
helm uninstall nrue gnb
kubectl delete -f oai5gcore/nfdeploy/
sleep 3
kubectl delete -f oai5gcore/controllerdeploy/
sleep 2
kubectl delete ns oaiops oai-upf oaicp
if [ "${USER}" ] && [ "${PASS}" ]; then
  ./ci-scripts/push-images.sh $TAG $PARENT $USER $PASS
fi
minikube delete
echo "----------Test Done ----------"