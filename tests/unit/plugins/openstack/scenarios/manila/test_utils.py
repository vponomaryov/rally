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

import itertools

import ddt
import mock

from rally.plugins.openstack.scenarios.manila import utils
from tests.unit import test

BM_UTILS = "rally.benchmark.utils."
MANILA_UTILS = "rally.plugins.openstack.scenarios.manila.utils.ManilaScenario."


@ddt.ddt
class ManilaScenarioTestCase(test.TestCase):

    def setUp(self):
        super(ManilaScenarioTestCase, self).setUp()
        self.scenario = utils.ManilaScenario()

    @mock.patch("time.sleep")
    @mock.patch(MANILA_UTILS + "clients")
    @mock.patch(BM_UTILS + "wait_for")
    @mock.patch(BM_UTILS + "get_from_manager")
    @mock.patch(BM_UTILS + "resource_is")
    def test__create_share(self, mock_resource_is, mock_get_from_manager,
                           mock_wait_for, mock_clients, mock_sleep):
        fake_name = "fake_name"
        fake_share = mock.Mock()
        mock_clients.return_value.shares.create.return_value = fake_share
        self.scenario.context = {
            "tenant": {
                "share_networks": ["sn_1_id", "sn_2_id", ],
            }
        }
        self.scenario.context["tenant"]["sn_iterator"] = itertools.cycle(
            self.scenario.context["tenant"]["share_networks"])
        self.scenario._generate_random_name = mock.Mock(return_value=fake_name)

        self.scenario._create_share("nfs")

        mock_clients.return_value.shares.create.assert_called_once_with(
            "nfs", 1, name=fake_name,
            share_network=self.scenario.context["tenant"]["share_networks"][0])

        mock_wait_for.assert_called_once_with(
            fake_share, is_ready=mock.ANY, update_resource=mock.ANY,
            timeout=300, check_interval=3)
        mock_resource_is.assert_called_once_with("available")
        mock_get_from_manager.assert_called_once_with()
        self.assertTrue(mock_sleep.called)

    @mock.patch(BM_UTILS + "get_from_manager")
    @mock.patch(BM_UTILS + "wait_for_delete")
    def test__delete_share(self, mock_wait_for_delete, mock_get_from_manager):
        fake_share = mock.MagicMock()

        self.scenario._delete_share(fake_share)

        fake_share.delete.assert_called_once_with()
        mock_get_from_manager.assert_called_once_with(("error_deleting", ))
        mock_wait_for_delete.assert_called_once_with(
            fake_share, update_resource=mock.ANY, timeout=180,
            check_interval=2)

    @ddt.data(
        {},
        {"detailed": False, "search_opts": None},
        {"detailed": True, "search_opts": {"name": "foo_sn"}},
        {"search_opts": {"project_id": "fake_project"}},
    )
    @mock.patch(MANILA_UTILS + "clients")
    def test__list_shares(self, params, mock_clients):
        fake_shares = ["foo", "bar"]
        mock_clients.return_value.shares.list.return_value = fake_shares

        result = self.scenario._list_shares(**params)

        self.assertEqual(fake_shares, result)
        mock_clients.return_value.shares.list.assert_called_once_with(
            detailed=params.get("detailed", True),
            search_opts=params.get("search_opts", None))

    @mock.patch(MANILA_UTILS + "clients")
    def test__create_share_network(self, mock_clients):
        fake_share = mock.Mock()
        mock_share_networks_client = mock_clients.return_value.share_networks
        mock_share_networks_client.create.return_value = fake_share
        data = {
            "neutron_net_id": "fake_neutron_net_id",
            "neutron_subnet_id": "fake_neutron_subnet_id",
            "nova_net_id": "fake_nova_net_id",
            "name": "fake_name",
            "description": "fake_description",
        }

        result = self.scenario._create_share_network(**data)

        self.assertEqual(fake_share, result)
        mock_share_networks_client.create.assert_called_once_with(**data)

    @mock.patch(BM_UTILS + "get_from_manager")
    @mock.patch(BM_UTILS + "wait_for_delete")
    def test__delete_share_network(self, mock_wait_for_delete,
                                   mock_get_from_manager):
        fake_sn = mock.MagicMock()

        self.scenario._delete_share_network(fake_sn)

        fake_sn.delete.assert_called_once_with()
        mock_get_from_manager.assert_called_once_with()
        mock_wait_for_delete.assert_called_once_with(
            fake_sn, update_resource=mock.ANY, timeout=180, check_interval=2)

    @ddt.data(
        {"detailed": True, "search_opts": {"name": "foo_sn"}},
        {"detailed": False, "search_opts": None},
        {},
        {"search_opts": {"project_id": "fake_project"}},
    )
    @mock.patch(MANILA_UTILS + "clients")
    def test__list_share_networks(self, params, mock_clients):
        fake_share_networks = ["foo", "bar"]
        mock_clients.return_value.share_networks.list.return_value = (
            fake_share_networks)

        result = self.scenario._list_share_networks(**params)

        self.assertEqual(fake_share_networks, result)
        mock_clients.return_value.share_networks.list.assert_called_once_with(
            detailed=params.get("detailed", True),
            search_opts=params.get("search_opts", None))

    @ddt.data(
        {},
        {"search_opts": None},
        {"search_opts": {"project_id": "fake_project"}},
    )
    @mock.patch(MANILA_UTILS + "clients")
    def test__list_share_servers(self, params, mock_clients):
        fake_share_servers = ["foo", "bar"]
        mock_clients.return_value.share_servers.list.return_value = (
            fake_share_servers)

        result = self.scenario._list_share_servers(**params)

        self.assertEqual(fake_share_servers, result)
        mock_clients.return_value.share_servers.list.assert_called_once_with(
            search_opts=params.get("search_opts", None))

    @ddt.data("ldap", "kerberos", "active_directory")
    @mock.patch(MANILA_UTILS + "clients")
    def test__create_security_service(self, ss_type, mock_clients):
        fake_ss = mock.Mock()
        mock_security_services_client = (
            mock_clients.return_value.security_services)
        mock_security_services_client.create.return_value = fake_ss
        data = {
            "type": ss_type,
            "dns_ip": "fake_dns_ip",
            "server": "fake_server",
            "domain": "fake_domain",
            "user": "fake_user",
            "password": "fake_password",
            "name": "fake_name",
            "description": "fake_description",
        }

        result = self.scenario._create_security_service(**data)

        self.assertEqual(fake_ss, result)
        mock_security_services_client.create.assert_called_once_with(**data)

    @mock.patch(BM_UTILS + "get_from_manager")
    @mock.patch(BM_UTILS + "wait_for_delete")
    def test__delete_security_service(self, mock_wait_for_delete,
                                      mock_get_from_manager):
        fake_ss = mock.MagicMock()

        self.scenario._delete_security_service(fake_ss)

        fake_ss.delete.assert_called_once_with()
        mock_get_from_manager.assert_called_once_with()
        mock_wait_for_delete.assert_called_once_with(
            fake_ss, update_resource=mock.ANY, timeout=180, check_interval=2)

    @mock.patch(MANILA_UTILS + "clients")
    def test__add_security_service_to_share_network(self, mock_clients):
        fake_sn = mock.MagicMock()
        fake_ss = mock.MagicMock()
        mock_share_networks_client = mock_clients.return_value.share_networks

        result = self.scenario._add_security_service_to_share_network(
            share_network=fake_sn, security_service=fake_ss)

        self.assertEqual(
            mock_share_networks_client.add_security_service.return_value,
            result)
        mock_share_networks_client.add_security_service.assert_has_calls([
            mock.call(fake_sn, fake_ss)])
