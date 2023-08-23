## Just a script to create minikube cluster for testing the operators
#/bin/bash
set -eo pipefail
#Remove a cluster if still running
minikube delete
#To create the vm
minikube start --driver=docker --cni=bridge --extra-config=kubeadm.pod-network-cidr=10.244.0.0/16 --cpus=4
rm -rf /tmp/multus && git clone https://github.com/k8snetworkplumbingwg/multus-cni.git /tmp/multus || true
kubectl create -f /tmp/multus/deployments/multus-daemonset-thick.yml
sleep 5
kubectl wait --for=condition=ready pod -l app=multus -n kube-system
# Enable the metrics server
minikube addons enable metrics-server

## Test if multus CNI is properly configured
kubectl create -f nad-test.yaml
kubectl wait --for=condition=ready pod -l app=testmultus
kubectl exec -it testpod -- ifconfig n3
echo "Cluster is properly configured"
