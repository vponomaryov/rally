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

from rally.benchmark.scenarios import base
from rally.benchmark import validation
from rally import consts
from rally import exceptions
from rally import osclients
from rally.plugins.openstack.scenarios.manila import utils as manila_utils


class ManilaShares(manila_utils.ManilaScenario):
    """Benchmark scenarios for Manila shares."""

    @validation.validate_share_proto()
    @validation.required_clients("manila")
    @validation.required_services(consts.Service.MANILA)
    @base.scenario()
    def create_and_delete_share(self, share_proto, size=1, min_sleep=0,
                                max_sleep=0, **kwargs):
        """Create and delete a share.

        Optional 'min_sleep' and 'max_sleep' parameters allow the scenario
        to simulate a pause between share creation and deletion
        (of random duration from [min_sleep, max_sleep]).

        :param share_proto: share protocol, valid values are NFS, CIFS,
            GlusterFS and HDFS
        :param size: share size in GB, should be greater than 0
        :param min_sleep: minimum sleep time in seconds (non-negative)
        :param max_sleep: maximum sleep time in seconds (non-negative)
        :param kwargs: optional args to create a share
        """
        share = self._create_share(
            share_proto=share_proto,
            size=size,
            **kwargs)
        self.sleep_between(min_sleep, max_sleep)
        self._delete_share(share)

    @validation.required_clients("manila")
    @validation.required_services(consts.Service.MANILA)
    @base.scenario()
    def list_shares(self, detailed=True, search_opts=None):
        """Basic scenario for 'share list' operation.

        :param detailed: defines either to return detailed list of
            objects or not.
        :param search_opts: container of search opts such as
            "name", "host", "share_type", etc.
        """
        self._list_shares(detailed=detailed, search_opts=search_opts)

    @validation.required_clients("manila")
    @validation.required_services(consts.Service.MANILA)
    @base.scenario()
    def create_share_network_and_delete(self,
                                        neutron_net_id=None,
                                        neutron_subnet_id=None,
                                        nova_net_id=None,
                                        name=None,
                                        description=None):
        """Creates share network and then deletes.

        :param neutron_net_id: ID of Neutron network
        :param neutron_subnet_id: ID of Neutron subnet
        :param nova_net_id: ID of Nova network
        :param name: share network name
        :param description: share network description
        """
        share_network = self._create_share_network(
            neutron_net_id=neutron_net_id,
            neutron_subnet_id=neutron_subnet_id,
            nova_net_id=nova_net_id,
            name=name,
            description=description,
        )
        self._delete_share_network(share_network)

    @validation.required_clients("manila")
    @validation.required_services(consts.Service.MANILA)
    @base.scenario(context={"cleanup": ["manila"]})
    def create_share_network_and_list(self,
                                      neutron_net_id=None,
                                      neutron_subnet_id=None,
                                      nova_net_id=None,
                                      name=None,
                                      description=None,
                                      detailed=True,
                                      search_opts=None):
        """Creates share network and then deletes.

        :param neutron_net_id: ID of Neutron network
        :param neutron_subnet_id: ID of Neutron subnet
        :param nova_net_id: ID of Nova network
        :param name: share network name
        :param description: share network description
        :param detailed: defines either to return detailed list of
            objects or not.
        :param search_opts: container of search opts such as
            "name", "nova_net_id", "neutron_net_id", etc.
        """
        self._create_share_network(
            neutron_net_id=neutron_net_id,
            neutron_subnet_id=neutron_subnet_id,
            nova_net_id=nova_net_id,
            name=name,
            description=description,
        )
        self._list_share_networks(
            detailed=detailed,
            search_opts=search_opts,
        )

    @validation.required_clients("manila")
    @validation.required_services(consts.Service.MANILA)
    @validation.required_openstack(admin=True)
    @base.scenario()
    def list_share_servers(self, search_opts=None):
        """Lists share servers.

        Requires admin creds.

        :param search_opts: container of following search opts:
            "host", "status", "share_network" and "project_id".
        """
        clients = osclients.Clients(self.context["admin"]["endpoint"])
        manila_scenario = manila_utils.ManilaScenario(clients=clients)
        manila_scenario._list_share_servers(search_opts=search_opts)

    @validation.required_clients("manila")
    @validation.required_services(consts.Service.MANILA)
    @base.scenario()
    def create_security_service_and_delete(self, type, dns_ip=None,
                                           server=None, domain=None, user=None,
                                           password=None, name=None,
                                           description=None):
        """Creates security service and then deletes.

        :param type: security service type - 'ldap', 'kerberos' or
                     'active_directory'
        :param dns_ip: dns ip address used inside tenant's network
        :param server: security service server ip address or hostname
        :param domain: security service domain
        :param user: security identifier used by tenant
        :param password: password used by user
        :param name: security service name
        :param description: security service description
        """
        security_service = self._create_security_service(
            type=type,
            dns_ip=dns_ip,
            server=server,
            domain=domain,
            user=user,
            password=password,
            name=name,
            description=description,
        )
        self._delete_security_service(security_service)

    @validation.required_clients("manila")
    @validation.required_services(consts.Service.MANILA)
    @base.scenario(context={"cleanup": ["manila"]})
    def attach_security_service_to_share_network(self,
                                                 security_service_type="ldap"):
        """Attaches security service to share network.

        :param security_service_type: type of security service to use.
            Should be one of following: 'ldap', 'kerberos' or
            'active_directory'.
        """
        sn = self._create_share_network()
        ss = self._create_security_service(type=security_service_type)
        self._add_security_service_to_share_network(sn, ss)

    @validation.validate_share_proto()
    @validation.required_clients("manila")
    @validation.required_services(consts.Service.MANILA)
    @base.scenario(context={"cleanup": ["manila"]})
    def create_and_list_share(self, share_proto, size=1, min_sleep=0,
                              max_sleep=0, detailed=True, **kwargs):
        """Create a share and list all shares.

        Optional 'min_sleep' and 'max_sleep' parameters allow the scenario
        to simulate a pause between share creation and list
        (of random duration from [min_sleep, max_sleep]).

        :param share_proto: share protocol, valid values are NFS, CIFS,
            GlusterFS and HDFS
        :param size: share size in GB, should be greater than 0
        :param min_sleep: minimum sleep time in seconds (non-negative)
        :param max_sleep: maximum sleep time in seconds (non-negative)
        :param detailed: defines whether to get detailed list of shares or not
        :param kwargs: optional args to create a share
        """
        self._create_share(share_proto=share_proto, size=size, **kwargs)
        self.sleep_between(min_sleep, max_sleep)
        self._list_shares(detailed=detailed)

    @validation.required_clients("manila")
    @validation.required_services(consts.Service.MANILA)
    @base.scenario()
    def set_and_delete_metadata(self, sets=10, set_size=3,
                                deletes=5, delete_size=3,
                                key_min_length=1, key_max_length=255,
                                value_min_length=1, value_max_length=1023):
        """Sets and deletes share metadata.

        This requires a share to be created with the shares
        context. Additionally, ``sets * set_size`` must be greater
        than or equal to ``deletes * delete_size``.

        :param sets: how many set_metadata operations to perform
        :param set_size: number of metadata keys to set in each
            set_metadata operation
        :param deletes: how many delete_metadata operations to perform
        :param delete_size: number of metadata keys to delete in each
            delete_metadata operation
        :param key_min_length: minimal size of metadata key to set
        :param key_max_length: maximum size of metadata key to set
        :param value_min_length: minimal size of metadata value to set
        :param value_max_length: maximum size of metadata value to set
        """
        if sets * set_size < deletes * delete_size:
            raise exceptions.InvalidArgumentsException(
                "Not enough metadata keys will be created: "
                "Setting %(num_keys)s keys, but deleting %(num_deletes)s" %
                {"num_keys": sets * set_size,
                 "num_deletes": deletes * delete_size})

        if len(self.context["tenant"].get("shares", [])) < 1:
            raise exceptions.InvalidContextSetup(
                reason=("This scenario requires, at least, one share to be "
                        "created in context. Please specify context option "
                        "'shares_per_tenant' bigger than 0"))

        share = random.choice(self.context["tenant"]["shares"])
        keys = self._set_metadata(
            share=share,
            sets=sets,
            set_size=set_size,
            key_min_length=key_min_length,
            key_max_length=key_max_length,
            value_min_length=value_min_length,
            value_max_length=value_max_length)
        self._delete_metadata(
            share=share, keys=keys, deletes=deletes, delete_size=delete_size)
