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
    def test__create_share(self, resource_is, get_from_manager, wait_for,
                           clients, sleep):
        fake_name = "fake_name"
        fake_share = mock.Mock()
        clients("manila").shares.create.return_value = fake_share
        self.scenario.context = {
            "tenant": {
                "share_networks": ["sn_1_id", "sn_2_id", ],
            }
        }
        self.scenario.context["tenant"]["sn_iterator"] = itertools.cycle(
            self.scenario.context["tenant"]["share_networks"])
        self.scenario._generate_random_name = mock.Mock(return_value=fake_name)

        self.scenario._create_share("nfs")

        clients("manila").shares.create.assert_called_once_with(
            "nfs", 1, name=fake_name,
            share_network=self.scenario.context["tenant"]["share_networks"][0])

        wait_for.assert_called_once_with(
            fake_share, is_ready=mock.ANY, update_resource=mock.ANY,
            timeout=300, check_interval=3)
        resource_is.assert_called_once_with("available")
        get_from_manager.assert_called_once_with()
        self.assertTrue(sleep.called)

    @mock.patch(BM_UTILS + "get_from_manager")
    @mock.patch(BM_UTILS + "wait_for_delete")
    def test__delete_share(self, wait_for_delete, get_from_manager):
        fake_share = type("Share", (object, ), {"delete": mock.Mock()})

        self.scenario._delete_share(fake_share)

        fake_share.delete.assert_called_once_with()
        get_from_manager.assert_called_once_with(("error_deleting", ))
        wait_for_delete.assert_called_once_with(
            fake_share, update_resource=mock.ANY, timeout=180,
            check_interval=2)

    @mock.patch(MANILA_UTILS + "clients")
    def test__create_share_network(self, clients):
        fake_share = mock.Mock()
        clients("manila").share_networks.create.return_value = fake_share
        data = {
            "neutron_net_id": "fake_neutron_net_id",
            "neutron_subnet_id": "fake_neutron_subnet_id",
            "nova_net_id": "fake_nova_net_id",
            "name": "fake_name",
            "description": "fake_description",
        }

        result = self.scenario._create_share_network(**data)

        self.assertEqual(fake_share, result)
        clients("manila").share_networks.create.assert_called_once_with(**data)

    @mock.patch(BM_UTILS + "get_from_manager")
    @mock.patch(BM_UTILS + "wait_for_delete")
    def test__delete_share_network(self, wait_for_delete, get_from_manager):
        fake_sn = type("ShareNetwork", (object, ), {"delete": mock.Mock()})

        self.scenario._delete_share_network(fake_sn)

        fake_sn.delete.assert_called_once_with()
        get_from_manager.assert_called_once_with()
        wait_for_delete.assert_called_once_with(
            fake_sn, update_resource=mock.ANY, timeout=180, check_interval=2)

    @ddt.data(
        {"detailed": True, "search_opts": {"name": "foo_sn"}},
        {"detailed": False, "search_opts": None},
        {},
        {"search_opts": {"project_id": "fake_project"}},
    )
    @mock.patch(MANILA_UTILS + "clients")
    def test__list_share_networks(self, params, clients):
        fake_share_networks = ["foo", "bar"]
        clients("manila").share_networks.list.return_value = (
            fake_share_networks)

        result = self.scenario._list_share_networks(**params)

        self.assertEqual(fake_share_networks, result)
        clients("manila").share_networks.list.assert_called_once_with(
            detailed=params.get("detailed", True),
            search_opts=params.get("search_opts", None))

    @ddt.data(
        {},
        {"search_opts": None},
        {"search_opts": {"project_id": "fake_project"}},
    )
    @mock.patch(MANILA_UTILS + "clients")
    def test__list_share_servers(self, params, clients):
        fake_share_servers = ["foo", "bar"]
        clients("manila").share_servers.list.return_value = (
            fake_share_servers)

        result = self.scenario._list_share_servers(**params)

        self.assertEqual(fake_share_servers, result)
        clients("manila").share_servers.list.assert_called_once_with(
            search_opts=params.get("search_opts", None))

    @ddt.data("ldap", "kerberos", "active_directory")
    @mock.patch(MANILA_UTILS + "clients")
    def test__create_security_service(self, ss_type, clients):
        fake_ss = mock.Mock()
        clients("manila").security_services.create.return_value = fake_ss
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
        clients("manila").security_services.create.assert_called_once_with(
            **data)

    @mock.patch(BM_UTILS + "get_from_manager")
    @mock.patch(BM_UTILS + "wait_for_delete")
    def test__delete_security_service(self, wait_for_delete, get_from_manager):
        fake_ss = type("SecurityService", (object, ), {"delete": mock.Mock()})

        self.scenario._delete_security_service(fake_ss)

        fake_ss.delete.assert_called_once_with()
        get_from_manager.assert_called_once_with()
        wait_for_delete.assert_called_once_with(
            fake_ss, update_resource=mock.ANY, timeout=180, check_interval=2)

    @mock.patch(MANILA_UTILS + "clients")
    def test__add_security_service_to_share_network(self, clients):
        fake_sn = mock.Mock()
        fake_ss = mock.Mock()
        clients("manila").share_networks.add_security_service.return_value = (
            fake_sn)

        result = self.scenario._add_security_service_to_share_network(
            share_network=fake_sn, security_service=fake_ss)

        self.assertEqual(fake_sn, result)
        clients("manila").share_networks.add_security_service.assert_has_calls(
            [mock.call(fake_sn, fake_ss)])
