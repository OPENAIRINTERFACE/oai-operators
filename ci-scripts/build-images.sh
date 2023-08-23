#/bin/bash
## To use
## ./build-images.sh $TAG $PARENT_DOCKER_REPO
set -eo pipefail

TAG=$1
PARENT=$2

docker build -f ../operators/amf/Dockerfile -t $PARENT/oai-amf-controller:$TAG ../operators/amf/ --no-cache
docker build -f ../operators/smf/Dockerfile -t $PARENT/oai-smf-controller:$TAG ../operators/smf/ --no-cache
docker build -f ../operators/upf/Dockerfile -t $PARENT/oai-upf-controller:$TAG ../operators/upf/ --no-cache
docker build -f ../operators/nrf/Dockerfile -t $PARENT/oai-nrf-controller:$TAG ../operators/nrf/ --no-cache
docker build -f ../operators/udr/Dockerfile -t $PARENT/oai-udr-controller:$TAG ../operators/udr/ --no-cache
docker build -f ../operators/udm/Dockerfile -t $PARENT/oai-udm-controller:$TAG ../operators/udm/ --no-cache
docker build -f ../operators/ausf/Dockerfile -t $PARENT/oai-ausf-controller:$TAG ../operators/ausf/ --no-cache

docker login
docker push $PARENT/oai-amf-controller:$TAG
docker push $PARENT/oai-smf-controller:$TAG
docker push $PARENT/oai-nrf-controller:$TAG
docker push $PARENT/oai-udr-controller:$TAG
docker push $PARENT/oai-udm-controller:$TAG
docker push $PARENT/oai-ausf-controller:$TAG
docker push $PARENT/oai-upf-controller:$TAG
docker logout
