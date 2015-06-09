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
from rally.plugins.openstack.scenarios.manila import utils as manila_utils


class ManilaShares(manila_utils.ManilaScenario):
    """Benchmark scenarios for Manila shares."""

    @validation.validate_share_proto()
    @validation.required_clients("manila")
    @validation.required_services(consts.Service.MANILA)
    @base.scenario()
    def create_and_delete_share(self, share_proto, size=1,
                                min_sleep=0, max_sleep=0, **kwargs):
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
            share, sets, set_size, key_min_length, key_max_length,
            value_min_length, value_max_length)
        self._delete_metadata(share, keys, deletes, delete_size)
