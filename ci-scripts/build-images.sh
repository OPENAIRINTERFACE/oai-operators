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
## To use
## ./build-images.sh $TAG $PARENT
set -eo pipefail

TAG=$1
PARENT=$2  #parent docker repo for re-tag and push
USER=$3
PASS=$4

docker build -f operators/amf/Dockerfile -t $PARENT/oai-amf-controller:$TAG operators/amf/ --no-cache
docker build -f operators/smf/Dockerfile -t $PARENT/oai-smf-controller:$TAG operators/smf/ --no-cache
docker build -f operators/upf/Dockerfile -t $PARENT/oai-upf-controller:$TAG operators/upf/ --no-cache
docker build -f operators/nrf/Dockerfile -t $PARENT/oai-nrf-controller:$TAG operators/nrf/ --no-cache
docker build -f operators/udr/Dockerfile -t $PARENT/oai-udr-controller:$TAG operators/udr/ --no-cache
docker build -f operators/udm/Dockerfile -t $PARENT/oai-udm-controller:$TAG operators/udm/ --no-cache
docker build -f operators/ausf/Dockerfile -t $PARENT/oai-ausf-controller:$TAG operators/ausf/ --no-cache

docker login -u $USER -p $PASS $PARENT
docker push $PARENT/oai-amf-controller:$TAG
docker push $PARENT/oai-smf-controller:$TAG
docker push $PARENT/oai-nrf-controller:$TAG
docker push $PARENT/oai-udr-controller:$TAG
docker push $PARENT/oai-udm-controller:$TAG
docker push $PARENT/oai-ausf-controller:$TAG
docker push $PARENT/oai-upf-controller:$TAG
docker logout