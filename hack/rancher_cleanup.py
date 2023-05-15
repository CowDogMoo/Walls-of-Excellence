import kubernetes.client
import kubernetes.config

CATTLE_NS = [
    "cattle-fleet-clusters-system",
    "cattle-fleet-local-system",
    "cattle-fleet-system",
    "cattle-global-data",
    "cattle-global-nt",
    "cattle-impersonation-system",
    "fleet-default",
    "fleet-local"
]

if __name__ == '__main__':
    configuration = kubernetes.config.load_kube_config()
    with kubernetes.client.ApiClient(configuration) as api_client:
        api_exts = kubernetes.client.ApiextensionsV1Api(api_client)
        api_cust = kubernetes.client.CustomObjectsApi(api_client)
        crds = api_exts.list_custom_resource_definition(timeout_seconds=30)
        for crd in crds.items:
            if 'cattle' not in crd.metadata.name:
                continue
            print('>=> %s' % crd.metadata.name)
            if crd.spec.scope == 'Namespaced':
                for ns in CATTLE_NS:
                    cust_objs = api_cust.list_namespaced_custom_object(
                        crd.spec.group,
                        crd.spec.versions[0].name,
                        ns,
                        crd.spec.names.plural
                    )
                    if len(cust_objs['items']) == 0:
                        continue
                    print("\t>=> ns: %s" % ns)
                    print("\t\t>=> %d objs" % len(cust_objs['items']))
                    for objx in cust_objs['items']:
                        print("\t\t\t>=> %s" % objx)
                        api_cust.delete_namespaced_custom_object(
                            crd.spec.group,
                            crd.spec.versions[0].name,
                            ns,
                            crd.spec.names.plural,
                            objx['metadata']['name']
                        )
                api_exts.delete_custom_resource_definition(crd.metadata.name)
            else:
                cust_objs = api_cust.list_cluster_custom_object(
                    crd.spec.group,
                    crd.spec.versions[0].name,
                    crd.spec.names.plural
                )
                if len(cust_objs['items']) == 0:
                    api_exts.delete_custom_resource_definition(crd.metadata.name)
                    continue
                print("\t>=> %s" % crd.spec.names.plural)
                print("\t\t>=> %d objs" % len(cust_objs['items']))
                for objx in cust_objs['items']:
                    print("\t\t\t>=> %s" % objx)
                    api_cust.patch_cluster_custom_object(
                        crd.spec.group,
                        crd.spec.versions[0].name,
                        crd.spec.names.plural,
                        objx['metadata']['name'],
                        {"metadata": {'finalizers': None}}
                    )
                    api_cust.delete_cluster_custom_object(
                        crd.spec.group,
                        crd.spec.versions[0].name,
                        crd.spec.names.plural,
                        objx['metadata']['name']
                    )
                api_exts.delete_custom_resource_definition(crd.metadata.name)