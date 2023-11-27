#!/bin/sh

PARENT='./crd'
BASE_URL="https://raw.githubusercontent.com/nephio-project/api/main/config/crd/bases"
wget $BASE_URL/ref.nephio.org_configs.yaml -O $PARENT/ref.nephio.org_configs.yaml || true
wget $BASE_URL/workload.nephio.org_nfdeployments.yaml -O $PARENT/workload.nephio.org_nfdeployments.yaml || true
wget $BASE_URL/workload.nephio.org_nfconfigs.yaml -O $PARENT/workload.nephio.org_nfconfigs.yaml || true
