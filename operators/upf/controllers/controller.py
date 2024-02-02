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


from jinja2 import Environment, FileSystemLoader
from pathlib import Path
## Most of the generic functions and environment variables are in utils
from utils import * 

import logging
import kopf
import time

@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    #OwnerReference
    if LOG_LEVEL == 'INFO':
        settings.posting.level = logging.INFO
    if LOG_LEVEL == 'ERROR':
        settings.posting.level = logging.ERROR
    if LOG_LEVEL == 'DEBUG':
        settings.posting.level = logging.DEBUG
    settings.persistence.finalizer = f"{NF_TYPE}.openairinterface.org"
    settings.persistence.progress_storage = kopf.AnnotationsProgressStorage(prefix=f"{NF_TYPE}.openairinterface.org")
    settings.persistence.diffbase_storage = kopf.AnnotationsDiffBaseStorage(
        prefix=f"{NF_TYPE}.openairinterface.org",
        key='last-handled-configuration',
    )

@kopf.on.resume(f"workload.nephio.org","NFDeployment", when=lambda spec, **_: spec.get('provider')==f"{NF_TYPE}.openairinterface.org")
@kopf.on.create(f"workload.nephio.org","NFDeployment", when=lambda spec, **_: spec.get('provider')==f"{NF_TYPE}.openairinterface.org")
def create_fn(spec, namespace, logger, patch, **kwargs):
    conf = yaml.safe_load(Path(OP_CONF_PATH).read_text())
    nf_resources = conf['compute']
    nrf_svc = None
    conf.update({
                'maxSubscribers': spec.get('maxSubscribers',1000),
                'interfaces': spec.get('interfaces'),
                'networkInstances': spec.get('networkInstances')
                })
    if 'imagePullSecrets' not in conf.keys():
        conf.update({'imagePullSecrets':None})
    if 'nad' not in conf.keys():
        conf.update({'nad':{'create':False}})
    data_networks = []
    for param_ref in spec.get('parametersRefs'):
        _temp = get_param_ref(name=param_ref['name'],namespace=namespace,logger=logger,
                            apiVersion=param_ref['apiVersion'],kind=param_ref['kind'].lower())
        if _temp['status'] and param_ref['kind']=='NFConfig':
            for _config in _temp['output']['spec']['configRefs']:
                conf.update({_config['kind']:_config['spec']})
        elif _temp['status'] and param_ref['kind']=='Config':
            conf.update(_temp['output']['spec']['config']['spec'])
    nf_ports = conf['ports']
    if 'fqdn' in conf.keys() and 'nrf' in conf['fqdn'].keys():
        nrf_svc = conf['fqdn']['nrf']
    data_networks = [y for i in conf['networkInstances'] if 'dataNetworks' in i for y in i['dataNetworks']] #taking out all the dataNetworks
    if len(data_networks)!=0 and 'PLMN' in conf.keys():
        for data_network in data_networks:
            # TODO: Consider nssai from all PLMNs
            for nssai in conf['PLMN']['plmnInfo'][0]['nssai']:
                for dnn in nssai['dnnInfo']:
                    if dnn['name'] == data_network['name']:
                        dnn.update({'subnet':data_network['pool'][0]['prefix']})

    # jinja rendering for nf configuration
    try:
        patch.status['observedGeneration'] = 0
        patch.status['conditions'] = [{'lastTransitionTime':datetime.now().strftime(TIME_FORMAT),
             'message':f"{kwargs['body']['metadata']['name']} pod(s) is(are) creating",
             'observedGeneration':0,
             'reason': f"MinimumReplicasNotAvailable",
             'status': "False",
             'type' : 'Progressing'
            }]
    except Exception as e:
        logger.error(f"Exception with reason {e}, in patching {name} in namespace {namespace}")
        raise kopf.PermanentError(f"Exception with reason {e}, in patching {name} in namespace {namespace}")

    svc_status = create_svc(name=f"oai-{NF_TYPE}",#kwargs['body']['metadata']['name'],
                          namespace=namespace,
                          labels=LABEL,
                          logger=logger,
                          ports=nf_ports,
                          kopf=kopf)
    conf['fqdn'].update({f"{NF_TYPE}":svc_status['name']}) ## the svc name of the nf is an input for nf configuration

    env = Environment(loader=FileSystemLoader(os.path.dirname(NF_CONF_PATH)))
    env.add_extension('jinja2.ext.do')
    jinja_template = env.get_template(os.path.basename(NF_CONF_PATH))
    configuration = jinja_template.render(conf=conf)
    cm_status = create_config_map(name=kwargs['body']['metadata']['name'], 
                                namespace=namespace,
                                labels=LABEL, 
                                configuration=configuration, 
                                logger=logger, 
                                kopf=kopf, 
                                nf_type=NF_TYPE)

    sa_status = create_sa(name=kwargs['body']['metadata']['name'], 
                          namespace=namespace,
                          labels=LABEL,
                          logger=logger,
                          kopf=kopf)

    if KUBERNETES_TYPE == 'openshift':
        rules = [
                    {
                      "apiGroups": ["security.openshift.io"],
                      "resourceNames": ["privileged"],
                      "resources": ["securitycontextconstraints"],
                      "verbs": ["use"]
                    }
                ]
        role_status = create_role(name=kwargs['body']['metadata']['name'], namespace=namespace, 
                                  logger=logger,
                                  labels=LABEL,
                                  rules=rules)
        if role_status['status']:
            role_binding_status = create_role_binding(name=kwargs['body']['metadata']['name'],
                                                      namespace=namespace,
                                                      sa_name=sa_status['name'],
                                                      role_name=kwargs['body']['metadata']['name'],
                                                      logger=logger,
                                                      labels=LABEL)

    deployment = create_deployment(name=kwargs['body']['metadata']['name'],
                                   namespace=namespace,
                                   compute=nf_resources, 
                                   labels= LABEL,
                                   nrf_svc=nrf_svc,
                                   image=conf['image'],
                                   interfaces=conf['interfaces'],
                                   nad=conf['nad'],
                                   image_pull_secrets=conf['imagePullSecrets'], 
                                   ports=nf_ports,
                                   config_map=cm_status['name'], 
                                   sa_name=sa_status['name'],
                                   nf_type=NF_TYPE,
                                   logger=logger,
                                   kopf=kopf)
    patch.status['conditions'][0] = {
             'lastTransitionTime':datetime.now().strftime(TIME_FORMAT),
             'message':deployment['message'],
             'observedGeneration':deployment['observedGeneration'],
             'reason': deployment['reason'],
             'status': deployment['status'],
             'type' : deployment['type']
            }
    if 'error' not in deployment.keys() or not deployment['error']:
        for i in range(1,DEPLOYMENT_FETCH_ITERATIONS):
            status=deployment_status(deployment_name=kwargs['body']['metadata']['name'],
                                    namespace=namespace,
                                    logger=logger,
                                    kopf=kopf)
            time.sleep(DEPLOYMENT_FETCH_INTERVAL)
            if status['ready']:
                patch.status['conditions'] = status['conditions']
                patch.status['observedGeneration'] = status['observedGeneration']
                kopf.info(kwargs['body'], reason='Logging', message=f"{NF_TYPE}deployments created", )
                break

@kopf.timer(f"workload.nephio.org","NFDeployment", when=lambda spec, **_: spec.get('provider')==f"{NF_TYPE}.openairinterface.org", initial_delay=30, interval=30.0, idle=100)
def reconcile_fn(spec, namespace, logger, patch, **kwargs):
    #fetch the current cm
    conf = yaml.safe_load(Path(OP_CONF_PATH).read_text())
    conf.update({
                'maxSubscribers': spec.get('maxSubscribers',1000),
                'interfaces': spec.get('interfaces'),
                'networkInstances': spec.get('networkInstances')
                })
    nf_resources = conf['compute']
    nrf_svc = None
    if 'fqdn' in conf.keys() and 'nrf' in conf['fqdn'].keys():
        nrf_svc = conf['fqdn']['nrf']
    if 'imagePullSecrets' not in conf.keys():
        conf.update({'imagePullSecrets':None})
    if 'nad' not in conf.keys():
        conf.update({'nad':{'create':False}})
    data_networks = []
    for param_ref in spec.get('parametersRefs'):
        _temp = get_param_ref(name=param_ref['name'],namespace=namespace,logger=logger,
                            apiVersion=param_ref['apiVersion'],kind=param_ref['kind'].lower())
        if _temp['status'] and param_ref['kind']=='NFConfig':
            for _config in _temp['output']['spec']['configRefs']:
                conf.update({_config['kind']:_config['spec']})
        elif _temp['status'] and param_ref['kind']=='Config':
            conf.update(_temp['output']['spec']['config']['spec'])
    nf_ports = conf['ports']
    if 'fqdn' in conf.keys() and 'nrf' in conf['fqdn'].keys():
        nrf_svc = conf['fqdn']['nrf']
    data_networks = [y for i in conf['networkInstances'] if 'dataNetworks' in i for y in i['dataNetworks']] #taking out all the dataNetworks
    if len(data_networks)!=0 and 'PLMN' in conf.keys():
        for data_network in data_networks:
            # TODO: Consider nssai from all PLMNs
            for nssai in conf['PLMN']['plmnInfo'][0]['nssai']:
                for dnn in nssai['dnnInfo']:
                    if dnn['name'] == data_network['name']:
                        dnn.update({'subnet':data_network['pool'][0]['prefix']})
    #fetch the current svc and declaring kubernetes api object
    try:
        api = kubernetes.client.CoreV1Api()
        obj = api.read_namespaced_service(
            namespace=namespace,
            name=f"oai-{NF_TYPE}"
            ).to_dict()
        svc_status = obj['metadata']
    except ApiException as e:
        if e.status == 404:
            svc_status = create_svc(name=f"oai-{NF_TYPE}",#kwargs['body']['metadata']['name'],
                                  namespace=namespace,
                                  labels=LABEL,
                                  logger=logger,
                                  ports=nf_ports,
                                  kopf=kopf)
    conf['fqdn'].update({f"{NF_TYPE}":svc_status['name']})   ## the svc name of the nf is an input for nf configuration
    env = Environment(loader=FileSystemLoader(os.path.dirname(NF_CONF_PATH)))
    env.add_extension('jinja2.ext.do')
    jinja_template = env.get_template(os.path.basename(NF_CONF_PATH))
    configuration = jinja_template.render(conf=conf)

    #fetch the config map(s)
    try:
        obj = api.read_namespaced_config_map(
            namespace=namespace,
            name=kwargs['body']['metadata']['name']
            ).to_dict()
        cm_name = obj['metadata']['name']
    except ApiException as e:
        if e.status == 404:
            cm_status = create_config_map(name=kwargs['body']['metadata']['name'], 
                                         namespace=namespace,
                                        labels=LABEL, 
                                        configuration=configuration, 
                                        logger=logger, 
                                        kopf=kopf, 
                                        nf_type=NF_TYPE)
            cm_name = cm_status['name']

    #fetch the current sa
    try:
        obj = api.read_namespaced_service_account(
            namespace=namespace,
            name=kwargs['body']['metadata']['name']
            ).to_dict()
        sa_name = obj['metadata']['name']
    except ApiException as e:
        if e.status == 404:
            sa_status = create_sa(name=kwargs['body']['metadata']['name'], 
                                  namespace=namespace,
                                  labels=LABEL,
                                  logger=logger,
                                  kopf=kopf)
            sa_name = sa_status['name']

    if KUBERNETES_TYPE == 'openshift' and not get_role(name=kwargs['body']['metadata']['name'], namespace=namespace, logger=logger)['status']:
        rules = [
                    {
                      "apiGroups": ["security.openshift.io"],
                      "resourceNames": ["privileged"],
                      "resources": ["securitycontextconstraints"],
                      "verbs": ["use"]
                    }
                ]
        role_status = create_role(name=kwargs['body']['metadata']['name'], namespace=namespace, 
                                  logger=logger,
                                  labels=LABEL,
                                  rules=rules)
    if KUBERNETES_TYPE == 'openshift' and not get_role_binding(name=kwargs['body']['metadata']['name'], namespace=namespace, logger=logger)['status']:
        role_binding_status = create_role_binding(name=kwargs['body']['metadata']['name'],
                                                  namespace=namespace,
                                                  sa_name=sa_name,
                                                  role_name=kwargs['body']['metadata']['name'],
                                                  logger=logger,
                                                  labels=LABEL)
    #fetch the current deployment
    try:
        api = kubernetes.client.AppsV1Api()
        obj = api.read_namespaced_deployment(
            namespace=namespace,
            name=kwargs['body']['metadata']['name']
            )
    except ApiException as e:
        if e.status == 404:
            patch.status['observedGeneration'] = 0
            patch.status['conditions'] = [{'lastTransitionTime':datetime.now().strftime(TIME_FORMAT),
                 'message':f"{kwargs['body']['metadata']['name']} pod(s) is(are) creating",
                 'observedGeneration':0,
                 'reason': f"MinimumReplicasNotAvailable",
                 'status': "False",
                 'type' : 'Progressing'
                }]
            deployment = create_deployment(name=kwargs['body']['metadata']['name'],
                                           namespace=namespace,
                                           compute=nf_resources, 
                                           labels= LABEL,
                                           image=conf['image'],
                                           nrf_svc=nrf_svc,
                                           interfaces=conf['interfaces'],
                                           nad=conf['nad'],
                                           image_pull_secrets=conf['imagePullSecrets'], 
                                           ports=nf_ports,
                                           config_map=cm_name, 
                                           sa_name=sa_name,
                                           nf_type=NF_TYPE,
                                           logger=logger,
                                           kopf=kopf)

            patch.status['conditions'][0] = {
                     'lastTransitionTime':datetime.now().strftime(TIME_FORMAT),
                     'message':deployment['message'],
                     'observedGeneration':deployment['observedGeneration'],
                     'reason': deployment['reason'],
                     'status': deployment['status'],
                     'type' : deployment['type']
                    }
            if 'error' not in deployment.keys() or not deployment['error']:
                for i in range(1,DEPLOYMENT_FETCH_ITERATIONS):
                    status=deployment_status(deployment_name=kwargs['body']['metadata']['name'],
                                            namespace=namespace,
                                            logger=logger,
                                            kopf=kopf)
                    time.sleep(DEPLOYMENT_FETCH_INTERVAL)
                    if status['ready']:
                        patch.status['conditions'] = status['conditions']
                        patch.status['observedGeneration'] = status['observedGeneration']
                        kopf.info(kwargs['body'], reason='Logging', message=f"{NF_TYPE}deployments created", )
                        break

@kopf.on.delete(f"workload.nephio.org","NFDeployment", when=lambda spec, **_: spec.get('provider')==f"{NF_TYPE}.openairinterface.org",optional=True)
def delete_fn(spec, name, namespace, logger, **kwargs):
    #Delete deployment
    try:
        api = kubernetes.client.AppsV1Api()
        obj = api.delete_namespaced_deployment(
                namespace=namespace,
                name=name,
            )
        logger.debug(f"Deployment deleted for network function: {name} from namespace: {namespace}")
    except ApiException as e:
        logger.debug(f"Exception {e} while deleting the Deployment for network function: {name} from namespace: {namespace}")

    #Delete cm
    try:
        api = kubernetes.client.CoreV1Api()
        obj = api.delete_namespaced_config_map(
                namespace=namespace,
                name=name,
            )
        logger.debug(f"Configmap deleted for network function: {name} from namespace: {namespace}")
    except ApiException as e:
        logger.debug(f"Exception {e} while deleting the ConfigMap for network function: {name} from namespace: {namespace}")

    #Delete sa
    try:
        api = kubernetes.client.CoreV1Api()
        obj = api.delete_namespaced_service_account(
                namespace=namespace,
                name=name,
            )
        logger.debug(f"Service account deleted for network function: {name} from namespace: {namespace}")
    except ApiException as e:
        logger.debug(f"Exception {e} while deleting the ServiceAccount for network function: {name} from namespace: {namespace}")

    #Delete svc
    try:
        api = kubernetes.client.CoreV1Api()
        obj = api.delete_namespaced_service(
                namespace=namespace,
                name=f"oai-{NF_TYPE}",
            )
        logger.debug(f"Service deleted for network function: {name} from namespace: {namespace}")
    except ApiException as e:
        logger.debug(f"Exception {e} while deleting the Service for network function: {name} from namespace: {namespace}")

    if KUBERNETES_TYPE == 'openshift' and get_role(name=kwargs['body']['metadata']['name'], namespace=namespace, logger=logger)['status']:
        delete_role(name=kwargs['body']['metadata']['name'], namespace=namespace, logger=logger)
        if get_role_binding(name=kwargs['body']['metadata']['name'], namespace=namespace, logger=logger)['status']:
            delete_role_binding(name=kwargs['body']['metadata']['name'], namespace=namespace, logger=logger)
    #Delete nad
    conf = yaml.safe_load(Path(OP_CONF_PATH).read_text())
    interfaces = spec.get('interfaces')
    if 'nad' in conf.keys() and conf['nad']['create'] and 'interfaces' != None:
        try:
            for interface in interfaces:
                _name = f"{name}-{interfaces.index(interface)}"
                delete_nad(name=_name,namespace=namespace,logger=logger)
        except ApiException as e:
            logger.debug(f"Exception {e} while deleting the network-attachment-definitions.k8s.cni.cncf.io for network function: {name} from namespace: {namespace}")


@kopf.on.update(f"workload.nephio.org","NFDeployment", when=lambda spec, **_: spec.get('provider')==f"{NF_TYPE}.openairinterface.org")
def update_fn(diff, spec, namespace, logger, patch, **kwargs):
    ## rejecting metadata related changes
    for op, field, old, new in diff:
        if 'metadata' in field:
            logger.debug(f"Rejecting metadata related changes. It is not implemented in this version.")
            return
    #Delete deployment
    name = kwargs['body']['metadata']['name']
    try:
        api = kubernetes.client.AppsV1Api()
        obj = api.delete_namespaced_deployment(
                namespace=namespace,
                name=name,
            )
        logger.debug(f"Deployment deleted for network function: {name} from namespace: {namespace}")
    except ApiException as e:
        logger.debug(f"Exception {e} while deleting the Deployment for network function: {name} from namespace: {namespace}")

    try:
        api = kubernetes.client.CoreV1Api()
        obj = api.delete_namespaced_config_map(
                namespace=namespace,
                name=name,
            )
        logger.debug(f"Configmap deleted for network function: {name} from namespace: {namespace}")
    except ApiException as e:
        logger.debug(f"Exception {e} while deleting the ConfigMap for network function: {name} from namespace: {namespace}")

    #fetch the current sa
    try:
        obj = api.read_namespaced_service_account(
            namespace=namespace,
            name=kwargs['body']['metadata']['name']
            ).to_dict()
        sa_name = obj['metadata']['name']
    except ApiException as e:
        if e.status == 404:
            sa_status = create_sa(name=kwargs['body']['metadata']['name'], 
                                  namespace=namespace,
                                  labels=LABEL,
                                  logger=logger,
                                  kopf=kopf)
            sa_name = sa_status['name']

    if KUBERNETES_TYPE == 'openshift' and not get_role(name=kwargs['body']['metadata']['name'], namespace=namespace, logger=logger)['status']:
        rules = [
                    {
                      "apiGroups": ["security.openshift.io"],
                      "resourceNames": ["privileged"],
                      "resources": ["securitycontextconstraints"],
                      "verbs": ["use"]
                    }
                ]
        role_status = create_role(name=kwargs['body']['metadata']['name'], namespace=namespace, 
                                  logger=logger,
                                  labels=LABEL,
                                  rules=rules)
    if KUBERNETES_TYPE == 'openshift' and not get_role_binding(name=kwargs['body']['metadata']['name'], namespace=namespace, logger=logger)['status']:
        role_binding_status = create_role_binding(name=kwargs['body']['metadata']['name'],
                                                  namespace=namespace,
                                                  sa_name=sa_name,
                                                  role_name=kwargs['body']['metadata']['name'],
                                                  logger=logger,
                                                  labels=LABEL)

    conf = yaml.safe_load(Path(OP_CONF_PATH).read_text())
    conf.update({
                'maxSubscribers': spec.get('maxSubscribers',1000),
                'interfaces': spec.get('interfaces'),
                'networkInstances': spec.get('networkInstances')
                })
    nf_resources = conf['compute']
    nrf_svc = None
    if 'fqdn' in conf.keys() and 'nrf' in conf['fqdn'].keys():
        nrf_svc = conf['fqdn']['nrf']
    if 'imagePullSecrets' not in conf.keys():
        conf.update({'imagePullSecrets':None})
    if 'nad' not in conf.keys():
        conf.update({'nad':{'create':False}})

    data_networks = []
    for param_ref in spec.get('parametersRefs'):
        _temp = get_param_ref(name=param_ref['name'],namespace=namespace,logger=logger,
                            apiVersion=param_ref['apiVersion'],kind=param_ref['kind'].lower())
        if _temp['status'] and param_ref['kind']=='NFConfig':
            for _config in _temp['output']['spec']['configRefs']:
                conf.update({_config['kind']:_config['spec']})
        elif _temp['status'] and param_ref['kind']=='Config':
            conf.update(_temp['output']['spec']['config']['spec'])
    nf_ports = conf['ports']
    if 'fqdn' in conf.keys() and 'nrf' in conf['fqdn'].keys():
        nrf_svc = conf['fqdn']['nrf']
    data_networks = [y for i in conf['networkInstances'] if 'dataNetworks' in i for y in i['dataNetworks']] #taking out all the dataNetworks
    if len(data_networks)!=0 and 'PLMN' in conf.keys():
        for data_network in data_networks:
            # TODO: Consider nssai from all PLMNs
            for nssai in conf['PLMN']['plmnInfo'][0]['nssai']:
                for dnn in nssai['dnnInfo']:
                    if dnn['name'] == data_network['name']:
                        dnn.update({'subnet':data_network['pool'][0]['prefix']})
    #fetch the current svc and declaring kubernetes api object
    try:
        api = kubernetes.client.CoreV1Api()
        obj = api.read_namespaced_service(
            namespace=namespace,
            name=f"oai-{NF_TYPE}"
            ).to_dict()
        svc_status = obj['metadata']
    except ApiException as e:
        if e.status == 404:
            svc_status = create_svc(name=f"oai-{NF_TYPE}",#kwargs['body']['metadata']['name'],
                                  namespace=namespace,
                                  labels=LABEL,
                                  logger=logger,
                                  ports=nf_ports,
                                  kopf=kopf)
    conf['fqdn'].update({f"{NF_TYPE}":svc_status['name']})   ## the svc name of the nf is an input for nf configuration

    env = Environment(loader=FileSystemLoader(os.path.dirname(NF_CONF_PATH)))
    env.add_extension('jinja2.ext.do')
    jinja_template = env.get_template(os.path.basename(NF_CONF_PATH))
    configuration = jinja_template.render(conf=conf)

    cm_status = create_config_map(name=name, 
                                namespace=namespace,
                                labels=LABEL, 
                                configuration=configuration, 
                                logger=logger, 
                                kopf=kopf, 
                                nf_type=NF_TYPE)

    deployment = create_deployment(name=kwargs['body']['metadata']['name'],
                                  namespace=namespace,
                                  compute=nf_resources, 
                                  labels=LABEL,
                                  nrf_svc=nrf_svc,
                                  image=conf['image'],
                                  interfaces=conf['interfaces'],
                                  nad=conf['nad'],
                                  image_pull_secrets=conf['imagePullSecrets'], 
                                  ports=nf_ports,
                                  config_map=cm_status['name'], 
                                  sa_name=sa_name,
                                  nf_type=NF_TYPE,
                                  logger=logger,
                                  kopf=kopf)

    if 'error' not in deployment.keys() or not deployment['error']:
        for i in range(1,DEPLOYMENT_FETCH_ITERATIONS):
            status=deployment_status(deployment_name=kwargs['body']['metadata']['name'],
                                    namespace=namespace,
                                    logger=logger,
                                    kopf=kopf)
            time.sleep(DEPLOYMENT_FETCH_INTERVAL)
            if status['ready']:
                patch.status['conditions'] = status['conditions']
                patch.status['observedGeneration'] = status['observedGeneration']
                kopf.info(kwargs['body'], reason='Logging', message=f"{NF_TYPE}deployments created", )
                break
