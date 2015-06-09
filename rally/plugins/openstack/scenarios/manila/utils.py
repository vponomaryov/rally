# Copyright 2015 Mirantis Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import random
import time

from oslo_config import cfg

from rally.benchmark.scenarios import base
from rally.benchmark import utils as bench_utils
from rally import exceptions


MANILA_BENCHMARK_OPTS = [
    cfg.FloatOpt(
        "manila_share_create_prepoll_delay",
        default=2.0,
        help="Delay between creating Manila share and polling for its "
             "status."),
    cfg.FloatOpt(
        "manila_share_create_timeout",
        default=300.0,
        help="Timeout for Manila share creation."),
    cfg.FloatOpt(
        "manila_share_create_poll_interval",
        default=3.0,
        help="Interval between checks when waiting for Manila share "
             "creation."),
    cfg.FloatOpt(
        "manila_share_delete_timeout",
        default=180.0,
        help="Timeout for Manila share deletion."),
    cfg.FloatOpt(
        "manila_share_delete_poll_interval",
        default=2.0,
        help="Interval between checks when waiting for Manila share "
             "deletion."),
]

CONF = cfg.CONF
benchmark_group = cfg.OptGroup(name="benchmark", title="benchmark options")
CONF.register_opts(MANILA_BENCHMARK_OPTS, group=benchmark_group)


class ManilaScenario(base.Scenario):
    """Base class for Manila scenarios with basic atomic actions."""

    @base.atomic_action_timer("manila.create_share")
    def _create_share(self, share_proto, size=1, **kwargs):
        """Create a share.

        :param share_proto: share protocol for new share,
            available values are NFS, CIFS, GlusterFS and HDFS.
        :param size: size of a share in GB
        :param snapshot_id: ID of the snapshot
        :param name: name of new share
        :param description: description of a share
        :param metadata: optional metadata to set on share creation
        :param share_network: either instance of ShareNetwork or str with ID
        :param share_type: either instance of ShareType or str with ID
        :param is_public: defines whether to set share as public or not.
        :returns: instance of :class:`Share`
        """
        if (self.context and
                self.context.get("tenant", {}).get("share_networks", []) and
                not kwargs.get("share_network")):
            kwargs["share_network"] = next(self.context.get("tenant", {}).get(
                "sn_iterator"))

        if not kwargs.get("name"):
            kwargs["name"] = self._generate_random_name()

        share = self.clients("manila").shares.create(
            share_proto, size, **kwargs)
        time.sleep(CONF.benchmark.manila_share_create_prepoll_delay)
        share = bench_utils.wait_for(
            share,
            is_ready=bench_utils.resource_is("available"),
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.manila_share_create_timeout,
            check_interval=CONF.benchmark.manila_share_create_poll_interval,
        )
        return share

    @base.atomic_action_timer("manila.delete_share")
    def _delete_share(self, share):
        """Delete the given share.

        :param share: :class:`Share`
        """
        share.delete()
        error_statuses = ("error_deleting", )
        bench_utils.wait_for_delete(
            share,
            update_resource=bench_utils.get_from_manager(error_statuses),
            timeout=CONF.benchmark.manila_share_delete_timeout,
            check_interval=CONF.benchmark.manila_share_delete_poll_interval)

    @base.atomic_action_timer("manila.list_shares")
    def _list_shares(self, detailed=True, search_opts=None):
        """Returns user shares list.

        :param detailed: defines either to return detailed list of
            objects or not.
        :param search_opts: container of search opts such as
            "name", "host", "share_type", etc.
        """
        return self.clients("manila").shares.list(
            detailed=detailed, search_opts=search_opts)

    @base.atomic_action_timer("manila.set_metadata")
    def _set_metadata(self, share, sets=1, set_size=1,
                      key_min_length=1, key_max_length=255,
                      value_min_length=1, value_max_length=1023):
        """Sets share metadata.

        :param share: the share to set metadata on
        :param sets: how many operations to perform
        :param set_size: number of metadata keys to set in each operation
        :param key_min_length: minimal size of metadata key to set
        :param key_max_length: maximum size of metadata key to set
        :param value_min_length: minimal size of metadata value to set
        :param value_max_length: maximum size of metadata value to set
        :returns: A list of keys that were set
        """
        keys = []
        if not (key_min_length < key_max_length or
                value_min_length < value_max_length):
            raise exceptions.InvalidArgumentsException(
                "Min length for keys and values of metadata should be smaller "
                "than maximum length.")
        elif key_min_length not in range(1, 256):
            raise exceptions.InvalidArgumentsException(
                "key_min_length '%s' is not in range(1, 256)" % key_min_length)
        elif key_max_length not in range(1, 256):
            raise exceptions.InvalidArgumentsException(
                "key_max_length '%s' is not in range(1, 256)" % key_max_length)
        elif value_min_length not in range(1, 1024):
            raise exceptions.InvalidArgumentsException(
                "value_min_length '%s' is not in range(1, 1024)" %
                value_min_length)
        elif value_max_length not in range(1, 1024):
            raise exceptions.InvalidArgumentsException(
                "value_max_length '%s' is not in range(1, 1024)" %
                value_max_length)

        for i in range(sets):
            metadata = {}
            for j in range(set_size):
                if key_min_length == key_max_length:
                    key_length = key_min_length
                else:
                    key_length = random.choice(
                        range(key_min_length, key_max_length))
                if value_min_length == value_max_length:
                    value_length = value_min_length
                else:
                    value_length = random.choice(
                        range(value_min_length, value_max_length))
                key = self._generate_random_name(prefix="", length=key_length)
                keys.append(key)
                value = self._generate_random_name(
                    prefix="", length=value_length)
                metadata[key] = value
            self.clients("manila").shares.set_metadata(share, metadata)

        return keys

    @base.atomic_action_timer("manila.delete_metadata")
    def _delete_metadata(self, share, keys, deletes=10, delete_size=3):
        """Deletes share metadata.

        :param share: The share to delete metadata from
        :param deletes: how many operations to perform
        :param delete_size: number of metadata keys to delete in each operation
        :param keys: a list of keys to choose deletion candidates from
        """
        if len(keys) < deletes * delete_size:
            raise exceptions.InvalidArgumentsException(
                "Not enough metadata keys to delete: "
                "%(num_keys)s keys, but asked to delete %(num_deletes)s" %
                {"num_keys": len(keys), "num_deletes": deletes * delete_size})
        for i in range(deletes):
            to_del = keys[i * delete_size:(i + 1) * delete_size]
            self.clients("manila").shares.delete_metadata(share, to_del)

    @base.atomic_action_timer("manila.create_share_network")
    def _create_share_network(self, neutron_net_id=None,
                              neutron_subnet_id=None,
                              nova_net_id=None, name=None, description=None):
        """Create share network.

        :param neutron_net_id: ID of Neutron network
        :param neutron_subnet_id: ID of Neutron subnet
        :param nova_net_id: ID of Nova network
        :param name: share network name
        :param description: share network description
        :returns: instance of :class:`ShareNetwork`
        """
        share_network = self.clients("manila").share_networks.create(
            neutron_net_id=neutron_net_id,
            neutron_subnet_id=neutron_subnet_id,
            nova_net_id=nova_net_id,
            name=name,
            description=description)
        return share_network

    @base.atomic_action_timer("manila.delete_share_network")
    def _delete_share_network(self, share_network):
        """Delete share network.

        :param share_network: instance of :class:`ShareNetwork`.
        """
        share_network.delete()
        bench_utils.wait_for_delete(
            share_network,
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.manila_share_delete_timeout,
            check_interval=CONF.benchmark.manila_share_delete_poll_interval)

    @base.atomic_action_timer("manila.list_share_networks")
    def _list_share_networks(self, detailed=True, search_opts=None):
        """List share networks.

        :param detailed: defines either to return detailed list of
            objects or not.
        :param search_opts: container of search opts such as
            "project_id" and "name".
        :returns: list of instances of :class:`ShareNetwork`
        """
        share_networks = self.clients("manila").share_networks.list(
            detailed=detailed, search_opts=search_opts)
        return share_networks

    @base.atomic_action_timer("manila.list_share_servers")
    def _list_share_servers(self, search_opts=None):
        """List share servers. Admin only.

        :param search_opts: set of key-value pairs to filter share servers by.
            Example: {"share_network": "share_network_name_or_id"}
        :returns: list of instances of :class:`ShareServer`
        """
        share_servers = self.clients("manila").share_servers.list(
            search_opts=search_opts)
        return share_servers

    @base.atomic_action_timer("manila.create_security_service")
    def _create_security_service(self, type, dns_ip=None, server=None,
                                 domain=None, user=None, password=None,
                                 name=None, description=None):
        """Create security service.

        'Security service' is data container in Manila that stores info
        about auth services 'Active Directory', 'Kerberos' and catalog
        service 'LDAP' that should be used for shares.

        :param type: security service type, permitted values are
            'ldap', 'kerberos' or 'active_directory'.
        :param dns_ip: dns ip address used inside tenant's network
        :param server: security service server ip address or hostname
        :param domain: security service domain
        :param user: security identifier used by tenant
        :param password: password used by user
        :param name: security service name
        :param description: security service description
        :returns: instance of :class:`SecurityService`
        """
        security_service = self.clients("manila").security_services.create(
            type=type,
            dns_ip=dns_ip,
            server=server,
            domain=domain,
            user=user,
            password=password,
            name=name,
            description=description)
        return security_service

    @base.atomic_action_timer("manila.delete_security_service")
    def _delete_security_service(self, security_service):
        """Delete security service.

        :param security_service: instance of :class:`SecurityService`.
        """
        security_service.delete()
        bench_utils.wait_for_delete(
            security_service,
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.manila_share_delete_timeout,
            check_interval=CONF.benchmark.manila_share_delete_poll_interval)

    @base.atomic_action_timer("manila.add_security_service_to_share_network")
    def _add_security_service_to_share_network(self, share_network,
                                               security_service):
        """Associate given security service with a share network.

        :param share_network: ID or instance of :class:`ShareNetwork`.
        :param security_service: ID or instance of :class:`SecurityService`.
        :returns: instance of :class:`ShareNetwork`.
        """
        share_network = self.clients(
            "manila").share_networks.add_security_service(
                share_network, security_service)
        return share_network
