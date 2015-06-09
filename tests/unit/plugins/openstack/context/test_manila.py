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

import copy
import itertools

import ddt
import mock
import six

from rally import consts
from rally import exceptions
from rally.plugins.openstack.context import manila as manila_context
from tests.unit import test

MANILA_UTILS_PATH = ("rally.plugins.openstack.scenarios.manila.utils."
                     "ManilaScenario.")


@ddt.ddt
class ManilaSampleGeneratorTestCase(test.TestCase):
    TENANTS_AMOUNT = 3
    USERS_PER_TENANT = 4
    SECURITY_SERVICES = [
        {"type": ss_type,
         "dns_ip": "fake_dns_ip_%s" % ss_type,
         "server": "fake_server_%s" % ss_type,
         "domain": "fake_domain_%s" % ss_type,
         "user": "fake_user_%s" % ss_type,
         "password": "fake_password_%s" % ss_type,
         "name": "fake_optional_name_%s" % ss_type}
        for ss_type in ("ldap", "kerberos", "active_directory")
    ]
    SHARES_PER_TENANT = 7

    def _get_context(self, use_security_services=False, networks_per_tenant=2,
                     neutron_network_provider=True):
        tenants = {}
        for t_id in range(self.TENANTS_AMOUNT):
            tenants[six.text_type(t_id)] = {"name": six.text_type(t_id)}
            tenants[six.text_type(t_id)]["networks"] = []
            for i in range(networks_per_tenant):
                network = {"id": "fake_net_id_%s" % i}
                if neutron_network_provider:
                    network["subnets"] = ["fake_subnet_id_of_net_%s" % i]
                else:
                    network["cidr"] = "101.0.5.0/24"
                tenants[six.text_type(t_id)]["networks"].append(network)
        users = []
        for t_id in tenants.keys():
            for i in range(self.USERS_PER_TENANT):
                users.append({"id": i, "tenant_id": t_id, "endpoint": "fake"})
        context = {
            "config": {
                "users": {
                    "tenants": self.TENANTS_AMOUNT,
                    "users_per_tenant": self.USERS_PER_TENANT,
                },
                "manila": {
                    "use_share_networks": True,
                    "share_networks": [],
                    "use_security_services": use_security_services,
                    "security_services": self.SECURITY_SERVICES,
                    "shares_per_tenant": self.SHARES_PER_TENANT,
                    "share_proto": "fake_share_proto",
                    "size": 13,
                },
                "network": {
                    "networks_per_tenant": networks_per_tenant,
                    "start_cidr": "101.0.5.0/24",
                },
            },
            "admin": {
                "endpoint": mock.MagicMock(),
            },
            "task": mock.MagicMock(),
            "users": users,
            "tenants": tenants,
        }
        return context

    def setUp(self):
        super(ManilaSampleGeneratorTestCase, self).setUp()
        self.ctxt_use_existing = {
            "task": mock.MagicMock(),
            "config": {
                "existing_users": {"foo": "bar"},
                "manila": {
                    "use_share_networks": True,
                    "share_networks": {
                        "tenant_1_id": ["sn_1_id", "sn_2_name"],
                        "tenant_2_name": ["sn_3_id", "sn_4_name", "sn_5_id"],
                    },
                    "shares_per_tenant": self.SHARES_PER_TENANT,
                    "share_proto": "fake_share_proto",
                    "size": 13,
                },
            },
            "tenants": {
                "tenant_1_id": {"id": "tenant_1_id", "name": "tenant_1_name"},
                "tenant_2_id": {"id": "tenant_2_id", "name": "tenant_2_name"},
            },
            "users": [
                {"tenant_id": "tenant_1_id", "endpoint": {"e1": "foo"}},
                {"tenant_id": "tenant_2_id", "endpoint": {"e2": "bar"}},
            ],
        }
        self.existing_sns = [
            type("ShareNetwork", (object, ), {
                "id": "sn_%s_id" % i, "name": "sn_%s_name" % i})
            for i in range(1, 6)
        ]

    def test_init(self):
        context = {}
        context["task"] = mock.MagicMock()
        context["config"] = {
            "manila": {"foo": "bar"},
            "not_manila": {"not_manila_key": "not_manila_value"},
        }

        inst = manila_context.Manila(context)

        self.assertEqual(context["config"]["manila"], inst.config)
        self.assertIn(consts.JSON_SCHEMA, inst.CONFIG_SCHEMA.get("$schema"))
        self.assertEqual(False, inst.CONFIG_SCHEMA.get("additionalProperties"))
        self.assertEqual("object", inst.CONFIG_SCHEMA.get("type"))
        props = inst.CONFIG_SCHEMA.get("properties", {})
        self.assertEqual({"type": "array"}, props.get("security_services"))
        self.assertEqual({"type": "object"}, props.get("share_networks"))
        self.assertEqual({"type": "boolean"}, props.get("use_share_networks"))
        self.assertEqual(
            {"type": "boolean"}, props.get("use_security_services"))
        self.assertEqual(
            {"type": "integer", "minimum": 0}, props.get("shares_per_tenant"))
        self.assertEqual({"type": "integer", "minimum": 1}, props.get("size"))
        self.assertEqual({"type": "string"}, props.get("share_proto"))
        self.assertEqual(450, inst.get_order())
        self.assertEqual("manila", inst.get_name())

    @mock.patch("rally.osclients.Clients")
    @mock.patch(MANILA_UTILS_PATH + "_create_share")
    def test_setup_share_networks_disabled(self, create_share, mock_osclients):
        ctxt = copy.deepcopy(self.ctxt_use_existing)
        ctxt["config"]["manila"]["use_share_networks"] = False
        inst = manila_context.Manila(ctxt)
        expected_ctxt = copy.deepcopy(ctxt)
        expected_ctxt["task"] = self.ctxt_use_existing["task"]
        for i in (1, 2):
            expected_ctxt["tenants"]["tenant_%s_id" % i]["shares"] = [
                create_share.return_value
                for j in range(self.SHARES_PER_TENANT)]

        inst.setup()

        self.assertEqual(expected_ctxt, inst.context)
        self.assertEqual(
            self.SHARES_PER_TENANT * len(self.ctxt_use_existing["tenants"]),
            create_share.call_count)

    @mock.patch("rally.osclients.Clients")
    @mock.patch(MANILA_UTILS_PATH + "_create_share")
    @mock.patch(MANILA_UTILS_PATH + "_list_share_networks")
    def test_setup_use_existing_share_networks(self, list_sns, create_share,
                                               mock_osclients):
        existing_sns = self.existing_sns
        inst = manila_context.Manila(self.ctxt_use_existing)
        list_sns.return_value = self.existing_sns
        expected_ctxt = copy.deepcopy(self.ctxt_use_existing)
        expected_ctxt.update({
            "manila_delete_share_networks": False,
            "tenants": {
                "tenant_1_id": {
                    "id": "tenant_1_id", "name": "tenant_1_name",
                    "share_networks": [sn for sn in existing_sns[0:2]],
                    "sn_iterator": mock.ANY,
                    "shares": [
                        create_share.return_value
                        for i in range(self.SHARES_PER_TENANT)],
                },
                "tenant_2_id": {
                    "id": "tenant_2_id", "name": "tenant_2_name",
                    "share_networks": [sn for sn in existing_sns[2:5]],
                    "sn_iterator": mock.ANY,
                    "shares": [
                        create_share.return_value
                        for i in range(self.SHARES_PER_TENANT)],
                },
            }
        })

        inst.setup()

        self.assertEqual(expected_ctxt["task"], inst.context.get("task"))
        self.assertEqual(expected_ctxt["config"], inst.context.get("config"))
        self.assertEqual(expected_ctxt["users"], inst.context.get("users"))
        self.assertEqual(
            False, inst.context.get("manila_delete_share_networks"))
        self.assertEqual(expected_ctxt["tenants"], inst.context.get("tenants"))
        self.assertEqual(
            self.SHARES_PER_TENANT * len(self.ctxt_use_existing["tenants"]),
            create_share.call_count)

        for i, sns in ((1, existing_sns[0:2]), (2, existing_sns[2:5])):
            sn_iterator = itertools.cycle(sns)
            for x in range(abs(self.SHARES_PER_TENANT - len(sns))):
                # Simulate calls spent on share creation
                next(sn_iterator)
            for j in range(12):
                self.assertEqual(
                    next(sn_iterator).id,
                    next(inst.context["tenants"]["tenant_%s_id" % i][
                        "sn_iterator"]).id)

    def test_setup_use_existing_share_networks_tenant_not_found(self):
        ctxt = copy.deepcopy(self.ctxt_use_existing)
        ctxt.update({"tenants": {}})
        inst = manila_context.Manila(ctxt)

        self.assertRaises(exceptions.ContextSetupFailure, inst.setup)

    @mock.patch("rally.osclients.Clients")
    @mock.patch(MANILA_UTILS_PATH + "_list_share_networks")
    def test_setup_use_existing_share_networks_sn_not_found(self, list_sns,
                                                            mock_osclients):
        ctxt = copy.deepcopy(self.ctxt_use_existing)
        ctxt["config"]["manila"]["share_networks"] = {"tenant_1_id": ["foo"]}
        inst = manila_context.Manila(ctxt)
        list_sns.return_value = self.existing_sns

        self.assertRaises(exceptions.ContextSetupFailure, inst.setup)

    def test_setup_use_existing_share_networks_with_empty_list(self):
        ctxt = copy.deepcopy(self.ctxt_use_existing)
        ctxt["config"]["manila"]["share_networks"] = {}
        inst = manila_context.Manila(ctxt)

        self.assertRaises(exceptions.ContextSetupFailure, inst.setup)

    @ddt.data(True, False)
    @mock.patch("rally.osclients.Clients")
    @mock.patch(MANILA_UTILS_PATH + "_create_share")
    @mock.patch(MANILA_UTILS_PATH + "_create_share_network")
    @mock.patch(MANILA_UTILS_PATH + "_create_security_service")
    @mock.patch(MANILA_UTILS_PATH + "_add_security_service_to_share_network")
    def test_setup_autocreate_share_networks_with_security_services(
            self, neutron, add_ss_to_sn, create_ss, create_sn, create_share,
            mock_osclients):
        networks_per_tenant = 2
        ctxt = self._get_context(
            networks_per_tenant=networks_per_tenant,
            neutron_network_provider=neutron,
            use_security_services=True,
        )
        inst = manila_context.Manila(ctxt)

        inst.setup()

        self.assertEqual(ctxt["task"], inst.context.get("task"))
        self.assertEqual(ctxt["config"], inst.context.get("config"))
        self.assertEqual(ctxt["users"], inst.context.get("users"))
        self.assertEqual(ctxt["tenants"], inst.context.get("tenants"))
        self.assertEqual(
            self.SHARES_PER_TENANT * self.TENANTS_AMOUNT,
            create_share.call_count)
        create_ss.assert_has_calls([
            mock.call(**ss) for ss in self.SECURITY_SERVICES])
        add_ss_to_sn.assert_has_calls([
            mock.call(mock.ANY, mock.ANY)
            for i in range(
                self.TENANTS_AMOUNT *
                networks_per_tenant *
                len(self.SECURITY_SERVICES))])
        if neutron:
            sn_args = {
                "name": mock.ANY,
                "neutron_net_id": mock.ANY,
                "neutron_subnet_id": mock.ANY,
            }
        else:
            sn_args = {"name": mock.ANY, "nova_net_id": mock.ANY}
        create_sn.assert_has_calls([
            mock.call(**sn_args)
            for i in range(self.TENANTS_AMOUNT * networks_per_tenant)])
        mock_osclients.assert_has_calls([
            mock.call("fake") for i in range(self.TENANTS_AMOUNT)])
        for t_id, t_ctxt in ctxt["tenants"].items():
            self.assertTrue(ctxt["tenants"][t_id].get("sn_iterator", False))

    @ddt.data(True, False)
    @mock.patch("rally.osclients.Clients")
    @mock.patch(MANILA_UTILS_PATH + "_create_share")
    @mock.patch(MANILA_UTILS_PATH + "_create_share_network")
    @mock.patch(MANILA_UTILS_PATH + "_create_security_service")
    @mock.patch(MANILA_UTILS_PATH + "_add_security_service_to_share_network")
    def test_setup_autocreate_share_networks_wo_security_services(
            self, neutron, add_ss_to_sn, create_ss, create_sn, create_share,
            mock_osclients):
        networks_per_tenant = 2
        ctxt = self._get_context(
            networks_per_tenant=networks_per_tenant,
            neutron_network_provider=neutron,
        )
        inst = manila_context.Manila(ctxt)

        inst.setup()

        self.assertEqual(ctxt["task"], inst.context.get("task"))
        self.assertEqual(ctxt["config"], inst.context.get("config"))
        self.assertEqual(ctxt["users"], inst.context.get("users"))
        self.assertEqual(ctxt["tenants"], inst.context.get("tenants"))
        self.assertFalse(create_ss.called)
        self.assertFalse(add_ss_to_sn.called)
        self.assertEqual(
            self.SHARES_PER_TENANT * self.TENANTS_AMOUNT,
            create_share.call_count)
        if neutron:
            sn_args = {
                "name": mock.ANY,
                "neutron_net_id": mock.ANY,
                "neutron_subnet_id": mock.ANY,
            }
        else:
            sn_args = {"name": mock.ANY, "nova_net_id": mock.ANY}
        create_sn.assert_has_calls([
            mock.call(**sn_args)
            for i in range(self.TENANTS_AMOUNT * networks_per_tenant)])
        mock_osclients.assert_has_calls([
            mock.call("fake") for i in range(self.TENANTS_AMOUNT)])
        for t_id, t_ctxt in ctxt["tenants"].items():
            self.assertTrue(ctxt["tenants"][t_id].get("sn_iterator", False))

    @mock.patch("rally.osclients.Clients")
    @mock.patch(MANILA_UTILS_PATH + "_create_share")
    @mock.patch(MANILA_UTILS_PATH + "_create_share_network")
    @mock.patch(MANILA_UTILS_PATH + "_create_security_service")
    @mock.patch(MANILA_UTILS_PATH + "_add_security_service_to_share_network")
    def test_setup_autocreate_share_networks_wo_networks(
            self, add_ss_to_sn, create_ss, create_sn, create_share,
            mock_osclients):
        ctxt = self._get_context(networks_per_tenant=0)
        inst = manila_context.Manila(ctxt)

        inst.setup()

        self.assertEqual(ctxt["task"], inst.context.get("task"))
        self.assertEqual(ctxt["config"], inst.context.get("config"))
        self.assertEqual(ctxt["users"], inst.context.get("users"))
        self.assertEqual(ctxt["tenants"], inst.context.get("tenants"))
        self.assertFalse(create_ss.called)
        self.assertFalse(add_ss_to_sn.called)
        self.assertEqual(
            self.SHARES_PER_TENANT * self.TENANTS_AMOUNT,
            create_share.call_count)
        create_sn.assert_has_calls([
            mock.call(name=mock.ANY) for i in range(self.TENANTS_AMOUNT)])
        mock_osclients.assert_has_calls([
            mock.call("fake") for i in range(self.TENANTS_AMOUNT)])
        for t_id, t_ctxt in ctxt["tenants"].items():
            self.assertTrue(ctxt["tenants"][t_id].get("sn_iterator", False))

    @mock.patch("rally.osclients.Clients")
    @mock.patch(MANILA_UTILS_PATH + "_delete_share")
    @mock.patch(MANILA_UTILS_PATH + "_create_share")
    @mock.patch(MANILA_UTILS_PATH + "_delete_share_network")
    @mock.patch(MANILA_UTILS_PATH + "_delete_security_service")
    @mock.patch(MANILA_UTILS_PATH + "_list_share_servers")
    @mock.patch(MANILA_UTILS_PATH + "_list_share_networks")
    def test_cleanup_used_existing_share_networks(
            self, list_sns, list_servers, delete_ss, delete_sn, create_share,
            delete_share, mock_osclients):
        inst = manila_context.Manila(self.ctxt_use_existing)
        list_sns.return_value = self.existing_sns
        inst.setup()

        inst.cleanup()

        self.assertFalse(list_servers.called)
        self.assertFalse(delete_ss.called)
        self.assertFalse(delete_sn.called)
        self.assertEqual(4, mock_osclients.call_count)
        self.assertEqual(
            self.SHARES_PER_TENANT * len(self.ctxt_use_existing["tenants"]),
            create_share.call_count)
        self.assertEqual(
            self.SHARES_PER_TENANT * len(self.ctxt_use_existing["tenants"]),
            delete_share.call_count)
        for user in self.ctxt_use_existing["users"]:
            self.assertIn(mock.call(user["endpoint"]),
                          mock_osclients.mock_calls)

    @ddt.data(True, False)
    @mock.patch("rally.benchmark.utils.wait_for_delete")
    @mock.patch("rally.osclients.Clients")
    @mock.patch(MANILA_UTILS_PATH + "_delete_share")
    @mock.patch(MANILA_UTILS_PATH + "_create_share")
    @mock.patch(MANILA_UTILS_PATH + "_delete_share_network")
    @mock.patch(MANILA_UTILS_PATH + "_delete_security_service")
    @mock.patch(MANILA_UTILS_PATH + "_create_share_network")
    @mock.patch(MANILA_UTILS_PATH + "_create_security_service")
    @mock.patch(MANILA_UTILS_PATH + "_add_security_service_to_share_network")
    @mock.patch(MANILA_UTILS_PATH + "_list_share_servers")
    def test_cleanup_autocreated_share_networks(
            self, use_security_services, list_servers, add_ss_to_sn, create_ss,
            create_sn, delete_ss, delete_sn, create_share, delete_share,
            mock_osclients, wait_for_delete):
        fake_share_servers = ["fake_share_server"]
        list_servers.return_value = fake_share_servers
        networks_per_tenant = 2
        ctxt = self._get_context(
            networks_per_tenant=networks_per_tenant,
            use_security_services=use_security_services,
        )
        inst = manila_context.Manila(ctxt)
        inst.setup()

        inst.cleanup()

        mock_osclients.assert_has_calls([
            mock.call("fake"),
            mock.call("fake"),
            mock.call("fake"),
            mock.call(ctxt["admin"]["endpoint"]),
        ])
        self.assertEqual(6, list_servers.call_count)
        list_servers.assert_has_calls([mock.call(search_opts=mock.ANY)])
        self.assertEqual(6, delete_sn.call_count)
        self.assertEqual(
            self.SHARES_PER_TENANT * self.TENANTS_AMOUNT,
            create_share.call_count)
        self.assertEqual(
            self.SHARES_PER_TENANT * self.TENANTS_AMOUNT,
            delete_share.call_count)
        self.assertEqual(
            18 if use_security_services else 0, delete_ss.call_count)
        self.assertEqual(
            6 + self.SHARES_PER_TENANT * self.TENANTS_AMOUNT,
            wait_for_delete.call_count)
        wait_for_delete.assert_has_calls([
            mock.call(fake_share_servers[0], update_resource=mock.ANY,
                      timeout=180, check_interval=2),
        ])
        self.assertEqual(self.SHARES_PER_TENANT * self.TENANTS_AMOUNT,
                         create_share.call_count)
