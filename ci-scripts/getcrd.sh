#!/bin/sh

PARENT='../crd'
BASE_URL="https://raw.githubusercontent.com/nephio-project/api/main/config/crd/bases"
wget $BASE_URL/ref.nephio.org_configs.yaml -O $PARENT/ref.nephio.org_configs.yaml
wget $BASE_URL/workload.nephio.org_amfdeployments.yaml -O $PARENT/workload.nephio.org_amfdeployments.yaml
wget $BASE_URL/workload.nephio.org_smfdeployments.yaml -O $PARENT/workload.nephio.org_smfdeployments.yaml
wget $BASE_URL/workload.nephio.org_upfdeployments.yaml -O $PARENT/workload.nephio.org_upfdeployments.yaml

## create crd for udr, udm, ausf, nrf
echo "At the moment nephio does not propose CRDs for UDR, UDM, NRF and AUSF"

cp $PARENT/workload.nephio.org_amfdeployments.yaml $PARENT/workload.nephio.org_nrfdeployments.yaml
cp $PARENT/workload.nephio.org_amfdeployments.yaml $PARENT/workload.nephio.org_udrdeployments.yaml
cp $PARENT/workload.nephio.org_amfdeployments.yaml $PARENT/workload.nephio.org_udmdeployments.yaml
cp $PARENT/workload.nephio.org_amfdeployments.yaml $PARENT/workload.nephio.org_ausfdeployments.yaml
sed -i 's/amf/nrf/g' $PARENT/workload.nephio.org_nrfdeployments.yaml
sed -i 's/amf/udr/g' $PARENT/workload.nephio.org_udrdeployments.yaml
sed -i 's/amf/udm/g' $PARENT/workload.nephio.org_udmdeployments.yaml
sed -i 's/amf/ausf/g' $PARENT/workload.nephio.org_ausfdeployments.yaml
sed -i 's/AMF/AUSF/g' $PARENT/workload.nephio.org_ausfdeployments.yaml
sed -i 's/AMF/NRF/g' $PARENT/workload.nephio.org_nrfdeployments.yaml
sed -i 's/AMF/UDR/g' $PARENT/workload.nephio.org_udrdeployments.yaml
sed -i 's/AMF/UDM/g' $PARENT/workload.nephio.org_udmdeployments.yaml
