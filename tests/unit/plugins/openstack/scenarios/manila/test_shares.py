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

from rally import exceptions
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
        {},
        {"detailed": True},
        {"detailed": False},
        {"search_opts": None},
        {"search_opts": {}},
        {"search_opts": {"foo": "bar"}},
        {"detailed": True, "search_opts": None},
        {"detailed": False, "search_opts": None},
        {"detailed": True, "search_opts": {"foo": "bar"}},
        {"detailed": False, "search_opts": {"quuz": "foo"}},
    )
    @ddt.unpack
    def test_list_shares(self, detailed=True, search_opts=None):
        scenario = shares.ManilaShares()
        scenario._list_shares = mock.MagicMock()

        scenario.list_shares(detailed=detailed, search_opts=search_opts)

        scenario._list_shares.assert_called_once_with(
            detailed=detailed, search_opts=search_opts)

    @ddt.data(
        {},
        {"name": "foo_name"},
        {"description": "foo_description"},
        {"neutron_net_id": "foo_neutron_net_id"},
        {"neutron_subnet_id": "foo_neutron_subnet_id"},
        {"nova_net_id": "foo_nova_net_id"},
        {"name": "foo_name",
         "description": "foo_description",
         "neutron_net_id": "foo_neutron_net_id",
         "neutron_subnet_id": "foo_neutron_subnet_id",
         "nova_net_id": "foo_nova_net_id"},
    )
    def test_create_share_network_and_delete(self, params):
        fake_sn = mock.MagicMock()
        scenario = shares.ManilaShares()
        scenario._create_share_network = mock.MagicMock(return_value=fake_sn)
        scenario._delete_share_network = mock.MagicMock()
        expected_params = {
            "name": None,
            "description": None,
            "neutron_net_id": None,
            "neutron_subnet_id": None,
            "nova_net_id": None,
        }
        expected_params.update(params)

        scenario.create_share_network_and_delete(**params)

        scenario._create_share_network.assert_called_once_with(
            **expected_params)
        scenario._delete_share_network.assert_called_once_with(fake_sn)

    @ddt.data(
        {},
        {"name": "foo_name"},
        {"description": "foo_description"},
        {"neutron_net_id": "foo_neutron_net_id"},
        {"neutron_subnet_id": "foo_neutron_subnet_id"},
        {"nova_net_id": "foo_nova_net_id"},
        {"name": "foo_name",
         "description": "foo_description",
         "neutron_net_id": "foo_neutron_net_id",
         "neutron_subnet_id": "foo_neutron_subnet_id",
         "nova_net_id": "foo_nova_net_id"},
    )
    def test_create_share_network_and_list(self, params):
        scenario = shares.ManilaShares()
        scenario._create_share_network = mock.MagicMock()
        scenario._list_share_networks = mock.MagicMock()
        expected_create_params = {
            "name": params.get("name"),
            "description": params.get("description"),
            "neutron_net_id": params.get("neutron_net_id"),
            "neutron_subnet_id": params.get("neutron_subnet_id"),
            "nova_net_id": params.get("nova_net_id"),
        }
        expected_list_params = {
            "detailed": params.get("detailed", True),
            "search_opts": params.get("search_opts"),
        }
        expected_create_params.update(params)

        scenario.create_share_network_and_list(**params)

        scenario._create_share_network.assert_called_once_with(
            **expected_create_params)
        scenario._list_share_networks.assert_called_once_with(
            **expected_list_params)

    @ddt.data(
        {},
        {"search_opts": None},
        {"search_opts": {}},
        {"search_opts": {"foo": "bar"}},
    )
    @mock.patch(
        "rally.plugins.openstack.scenarios.manila.utils.ManilaScenario")
    @mock.patch("rally.osclients.Clients")
    def test_list_share_servers(self, search_opts, mock_osclients,
                                mock_manila_scenario):
        scenario = shares.ManilaShares()
        scenario.context = {"admin": {"endpoint": "fake_endpoint"}}
        scenario._list_share_servers = mock.MagicMock()

        scenario.list_share_servers(search_opts=search_opts)

        mock_manila_scenario.return_value._list_share_servers.assert_has_calls(
            mock.call(search_opts=search_opts))
        mock_osclients.assert_called_once_with(
            scenario.context["admin"]["endpoint"])
        mock_manila_scenario.assert_called_once_with(
            clients=mock_osclients.return_value)

    @ddt.data(
        {"type": "fake_type"},
        {"name": "foo_name",
         "type": "fake_type",
         "dns_ip": "fake_dns_ip",
         "server": "fake_server",
         "domain": "fake_domain",
         "user": "fake_user",
         "password": "fake_password",
         "description": "fake_description"},
    )
    def test_create_security_service_and_delete(self, params):
        fake_ss = mock.MagicMock()
        scenario = shares.ManilaShares()
        scenario._create_security_service = mock.MagicMock(
            return_value=fake_ss)
        scenario._delete_security_service = mock.MagicMock()
        expected_params = {
            "type": params.get("type"),
            "dns_ip": params.get("dns_ip"),
            "server": params.get("server"),
            "domain": params.get("domain"),
            "user": params.get("user"),
            "password": params.get("password"),
            "name": params.get("name"),
            "description": params.get("description"),
        }
        expected_params.update(params)

        scenario.create_security_service_and_delete(**params)

        scenario._create_security_service.assert_called_once_with(
            **expected_params)
        scenario._delete_security_service.assert_called_once_with(fake_ss)

    @ddt.data("ldap", "kerberos", "active_directory")
    def test_attach_security_service_to_share_network(self,
                                                      security_service_type):
        scenario = shares.ManilaShares()
        scenario._create_share_network = mock.MagicMock()
        scenario._create_security_service = mock.MagicMock()
        scenario._add_security_service_to_share_network = mock.MagicMock()

        scenario.attach_security_service_to_share_network(
            security_service_type=security_service_type)

        scenario._create_share_network.assert_called_once_with()
        scenario._create_security_service.assert_called_once_with(
            type=security_service_type)
        scenario._add_security_service_to_share_network.assert_has_calls(
            mock.call(scenario._create_share_network.return_value,
                      scenario._create_security_service.return_value))

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

    @ddt.data(
        {"sets": 4, "set_size": 5, "deletes": 3, "delete_size": 7},
    )
    def test_set_and_delete_metadata_wrong_data(self, params):
        scenario = shares.ManilaShares()
        self.assertRaises(
            exceptions.InvalidArgumentsException,
            scenario.set_and_delete_metadata,
            **params)

    @ddt.data(
        {"tenant": {}},
        {"tenant": {"shares": []}},
    )
    def test_set_and_delete_metadata_no_shares_in_context(self, context):
        scenario = shares.ManilaShares()
        scenario.context = context
        self.assertRaises(
            exceptions.InvalidContextSetup,
            scenario.set_and_delete_metadata)

    @ddt.data(
        {},
        {"sets": 5, "set_size": 8, "deletes": 4, "delete_size": 10},
    )
    @mock.patch("random.choice")
    def test_set_and_delete_metadata(self, params, mock_random_choice):
        scenario = shares.ManilaShares()
        scenario.context = {"tenant": {"shares": ["fake_share"]}}
        scenario._set_metadata = mock.MagicMock()
        scenario._delete_metadata = mock.MagicMock()
        expected_set_params = {
            "share": mock_random_choice.return_value,
            "sets": params.get("sets", 10),
            "set_size": params.get("set_size", 3),
            "key_min_length": params.get("key_min_length", 1),
            "key_max_length": params.get("key_max_length", 255),
            "value_min_length": params.get("value_min_length", 1),
            "value_max_length": params.get("value_max_length", 1023),
        }

        scenario.set_and_delete_metadata(**params)

        mock_random_choice.assert_called_once_with(
            scenario.context["tenant"]["shares"])
        scenario._set_metadata.assert_called_once_with(**expected_set_params)
        scenario._delete_metadata.assert_called_once_with(
            share=mock_random_choice.return_value,
            keys=scenario._set_metadata.return_value,
            deletes=params.get("deletes", 5),
            delete_size=params.get("delete_size", 3),
        )
