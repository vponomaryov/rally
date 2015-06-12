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

from rally.benchmark.scenarios import base
from rally.benchmark import validation
from rally import consts
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
