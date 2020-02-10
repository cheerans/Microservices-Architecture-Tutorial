import json
import logging
import os
import threading

import docker
import urllib3
from docker.types import ServiceMode

from com.autoscaler.exception.ServiceNotFoundException import ServiceNotFoundException

logger = logging.getLogger(__name__)

def jsons(resp):
    pass

class DockerService(object):
    def __init__(self):
        self.docker_engine = docker.from_env()

    def get_req_rate(self,service_name):
        req_rate = None
        req_count_url = os.environ["REQ_COUNT_URL"]
        logger.info("REQ_COUNT_URL {}".format(req_count_url))
        resp = urllib3.PoolManager().request('GET',req_count_url)
        resp = json.loads(resp.data.decode('utf-8'))
        if 'measurements' in resp:
            resp=next(filter(lambda x: x['statistic'] == 'COUNT', resp['measurements']))
            if 'value' in resp:
                req_rate = int(resp['value'])
        return req_rate

    def get_cpu_usage(self,service_name):

        try:
            client = docker.from_env()
            logger.info("HERE11")
            containerLst = client.containers.list()
            logger.info("HERE1")
            cpu_usage = None
            system_cpu_usage = None
            cpu_count = None

            service_count = 0
            for container in containerLst:
                stats = container.stats(stream=False)
                if service_name in stats['name']:
                    service_count += 1
                    cpu_usage += stats['cpu_stats']['cpu_usage']['total_usage']
                    system_cpu_usage += stats['cpu_stats']['system_cpu_usage']
                    cpu_count += stats['cpu_stats']['online_cpus']
        except Exception as e:
            logger.info(e.__str__())
        if service_count > 0:
            cpu_usage = cpu_usage / service_count
            system_cpu_usage = system_cpu_usage / service_count
            online_cpus = cpu_count / service_count
        return cpu_usage, system_cpu_usage, online_cpus

    def _get_service(self, service_name):
        services = self.docker_engine.services.list(filters=dict(name=service_name))            
        if (not services):
            raise ServiceNotFoundException(service_name)                     
        return services[0]

    def get_service_replica_count(self, service_name):
        service = self._get_service(service_name)
        return service.attrs['Spec']['Mode']['Replicated']['Replicas']

    def scale_service(self, service_name, replica_count):
        service = self._get_service(service_name)
        service.update(mode=ServiceMode("replicated", replicas=replica_count))
