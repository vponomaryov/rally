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

import ddt
import mock

from rally.plugins.openstack.scenarios.manila import shares
from tests.unit import test


@ddt.ddt
class ManilaSharesTestCase(test.TestCase):

    @ddt.data(
        {"share_proto": "nfs", "size": 3},
        {"share_proto": "cifs", "size": 4,
         "share_network": "foo", "share_type": "bar"},
    )
    def test_create_and_delete_share(self, params):
        fake_share = mock.MagicMock()
        scenario = shares.ManilaShares()
        scenario._create_share = mock.MagicMock(return_value=fake_share)
        scenario.sleep_between = mock.MagicMock()
        scenario._delete_share = mock.MagicMock()

        scenario.create_and_delete_share(min_sleep=3, max_sleep=4, **params)

        scenario._create_share.assert_called_once_with(**params)
        scenario.sleep_between.assert_called_once_with(3, 4)
        scenario._delete_share.assert_called_once_with(fake_share)

    @ddt.data(
        {"share_proto": "nfs", "size": 3, "detailed": True},
        {"share_proto": "cifs", "size": 4, "detailed": False,
         "share_network": "foo", "share_type": "bar"},
    )
    def test_create_and_list_share(self, params):
        scenario = shares.ManilaShares()
        scenario._create_share = mock.MagicMock()
        scenario.sleep_between = mock.MagicMock()
        scenario._list_shares = mock.MagicMock()

        scenario.create_and_list_share(min_sleep=3, max_sleep=4, **params)

        detailed = params.pop("detailed")
        scenario._create_share.assert_called_once_with(**params)
        scenario.sleep_between.assert_called_once_with(3, 4)
        scenario._list_shares.assert_called_once_with(detailed=detailed)
