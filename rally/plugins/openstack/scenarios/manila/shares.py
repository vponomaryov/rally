# Copyright 2015: Mirantis Inc.
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

    @validation.verify_share_proto()
    @validation.required_clients("manila")
    @validation.required_services(consts.Service.MANILA)
    @base.scenario()
    def create_delete_shares(self, share_proto=None, size=1,
                             min_sleep=0, max_sleep=0, **kwargs):
        """Create and delete a share.

        :param share_proto: text -- share protocol
        :param size: int -- share size in GB, should be greater than 0
        :param min_sleep: int -- minimum sleep time in seconds (non-negative)
        :param max_sleep: int -- maximum sleep time in seconds (non-negative)
        :param kwargs: optional args to create a share
        """
        share = self._create_share(
            share_proto=share_proto,
            size=size,
            **kwargs)
        self.sleep_between(min_sleep, max_sleep)
        self._delete_share(share)
