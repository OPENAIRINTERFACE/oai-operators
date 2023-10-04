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

FROM python:3.11-alpine3.17 as builder
COPY controllers/controller.py \
	 controllers/utils.py \
	 requirements.txt \
	 /src/
RUN pip install --user -r /src/requirements.txt --no-cache-dir
############### Target
FROM python:3.11-alpine3.17 as target
COPY --from=builder /root/.local \
					/src/controller.py \
					/src/utils.py \
					/root/.local
ENV PATH=/root/.local/bin:$PATH
CMD kopf run /root/.local/controller.py --all-namespaces