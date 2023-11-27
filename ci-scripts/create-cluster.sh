## Just a script to create minikube cluster for testing the operators
#/bin/bash
set -eo pipefail
configure_metallb_for_minikube() {
  # determine load balancer ingress range
  CIDR_BASE_ADDR="$(minikube ip)"
  INGRESS_FIRST_ADDR="$(echo "${CIDR_BASE_ADDR}" | awk -F'.' '{print $1,$2,$3,3}' OFS='.')"
  INGRESS_LAST_ADDR="$(echo "${CIDR_BASE_ADDR}" | awk -F'.' '{print $1,$2,$3,253}' OFS='.')"

  CONFIG_MAP="apiVersion: v1
kind: ConfigMap
metadata:
  namespace: metallb-system
  name: config
data:
  config: |
    address-pools:
    - name: default
      protocol: layer2
      addresses:
      - $INGRESS_FIRST_ADDR - $INGRESS_LAST_ADDR"

  # configure metallb ingress address range
  echo "${CONFIG_MAP}" | kubectl apply -f -
  echo "Ip-address range from $INGRESS_FIRST_ADDR to $INGRESS_LAST_ADDR for internet network or LoadBalancer"
}
#Remove a cluster if still running
minikube delete
minikube start --driver=docker --cni=bridge --extra-config=kubeadm.pod-network-cidr=10.244.0.0/16 --cpus=4 --memory=16G --addons=metallb --addons=metrics-server
sleep 20
rm -rf /tmp/multus && git clone https://github.com/k8snetworkplumbingwg/multus-cni.git /tmp/multus || true
kubectl create -f /tmp/multus/deployments/multus-daemonset.yml
sleep 40
kubectl wait --for=condition=ready pod -l app=multus -n kube-system --timeout=2m
configure_metallb_for_minikube
## Test if multus CNI is properly configured
kubectl create -f `pwd`/ci-scripts/nad-test.yaml
kubectl wait --for=condition=ready pod -l app=testmultus
kubectl exec -it testpod -- ifconfig n3
kubectl delete -f `pwd`/ci-scripts/nad-test.yaml
#fetch the crds from nephio repository
./ci-scripts/getcrd.sh
kubectl create -f `pwd`/crd/
nohup kubectl proxy --port 8080 &>/dev/null &
echo "Cluster is properly configured and proxy is running at 8080"