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

from oslo_config import cfg

from rally.benchmark import context
from rally.benchmark.scenarios import base as scenario_base
from rally.benchmark import utils as bench_utils
from rally.common.i18n import _
from rally.common import log
from rally.common import utils
from rally import consts
from rally import exceptions
from rally import osclients
from rally.plugins.openstack.scenarios.manila import utils as manila_utils

CONF = cfg.CONF
LOG = log.getLogger(__name__)


@context.context(name="manila", order=450)
class Manila(context.Context):
    """This context creates resources specific for Manila project."""
    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            # NOTE(vponomaryov): specifies whether manila should use
            # share networks for share creation or not.
            "use_share_networks": {"type": "boolean"},

            # NOTE(vponomaryov): if context arg 'share_networks' has values
            # then they will be used else share networks will be autocreated -
            # one for each tenant network. If networks do not exist then will
            # be created one share network for each tenant without network
            # data. This context arg will be used only when context arg
            # "use_share_networks" is set to True and context 'existing_users'
            # is not empty, considering usage of existing users.
            # Expected value is list of dicts where tenant Name or ID is key
            # and list of share_network Names or IDs is value. Example:
            # share_networks = [
            #     {"tenant_1_name_or_id": ["share_network_1_name_or_id",
            #                              "share_network_2_name_or_id"]},
            #     {"tenant_2_name_or_id": ["share_network_3_name_or_id"]}
            # ]
            # Also, make sure that all 'existing users' in appropriate
            # registered deployment have share networks if its usage is
            # enbaled, else Rally will randomly take users that does not
            # satisfy criteria.
            "share_networks": {"type": "object"},

            # NOTE(vponomaryov): following settings will be used only if share
            # networks are used and autocreated.
            "use_security_services": {"type": "boolean"},

            # NOTE(vponomaryov): context arg 'security_services' is expected
            # to be list of dicts with data for creation of security services.
            # Example:
            # security_services = [
            #     {'type': 'LDAP', 'dns_ip': 'foo_ip', 'server': 'bar_ip',
            #      'domain': 'quuz_domain', 'user': 'ololo',
            #      'password': 'fake_password', 'name': 'optional_name'}
            # ]
            # Where 'type' is required key and should have one of following
            # values: 'active_directory', 'kerberos' or 'ldap'.
            "security_services": {"type": "array"},

            # NOTE(vponomaryov): set it bigger than zero only if scenarios that
            # use precreated shares will be run.
            "shares_per_tenant": {
                "type": "integer",
                "minimum": 0,
            },
            # NOTE(vponomaryov): size and share_proto are used for creation of
            # shares.
            "size": {
                "type": "integer",
                "minimum": 1
            },
            "share_proto": {
                "type": "string",
            },
        },
        "additionalProperties": False
    }
    DEFAULT_CONFIG = {
        "use_share_networks": True,
        "share_networks": [],
        "use_security_services": False,
        "security_services": [],

        "shares_per_tenant": 0,
        "size": 1,
        "share_proto": "NFS",
    }

    def _setup_for_existing_users(self):
        if (self.config["use_share_networks"] and
                not self.config["share_networks"]):
            msg = _("Usage of share networks was enabled but for deployment "
                    "with existing users share networks also should be "
                    "specified via arg 'share_networks'")
            raise exceptions.ContextSetupFailure(
                ctx_name=self.get_name(), msg=msg)

        # Set flag that says we will not delete/cleanup share networks
        self.context["manila_delete_share_networks"] = False

        for tenant_name_or_id, share_networks in self.config[
                "share_networks"].items():
            # Verify project existence
            for tenant in self.context["tenants"].values():
                if tenant_name_or_id in (tenant["id"], tenant["name"]):
                    tenant_id = tenant["id"]
                    endpoint = None
                    for user in self.context["users"]:
                        if user["tenant_id"] == tenant_id:
                            endpoint = user["endpoint"]
                            break
                    break
            else:
                msg = _("Provided tenant Name or ID '%s' was not found in "
                        "existing tenants.") % tenant_name_or_id
                raise exceptions.ContextSetupFailure(
                    ctx_name=self.get_name(), msg=msg)
            self.context["tenants"][tenant_id]["share_networks"] = []

            clients = osclients.Clients(endpoint)
            manila_scenario = manila_utils.ManilaScenario(clients=clients)
            existing_sns = manila_scenario._list_share_networks(
                detailed=False, search_opts={"project_id": tenant_id})

            for sn_name_or_id in share_networks:
                # Verify share network existence
                for sn in existing_sns:
                    if sn_name_or_id in (sn.id, sn.name):
                        break
                else:
                    msg = _("Specified share network '%(sn)s' does not "
                            "exist for tenant '%(t)s'") % {
                                "sn": sn_name_or_id, "t": tenant_id}
                    raise exceptions.ContextSetupFailure(
                        ctx_name=self.get_name(), msg=msg)

                # Set share network for project
                self.context["tenants"][tenant_id][
                    "share_networks"].append(sn)

            # Add generator over share networks for each project
            self.context["tenants"][tenant_id]["sn_iterator"] = (
                itertools.cycle(
                    self.context["tenants"][tenant_id]["share_networks"]))

            # Create shares
            self._create_shares(
                manila_scenario,
                tenant_id,
                self.config["share_proto"],
                self.config["size"])

    def _setup_for_autocreated_users(self):
        # Create share network for each network of tenant
        for user, tenant_id in (utils.iterate_per_tenants(
                self.context.get("users", []))):
            networks = self.context["tenants"][tenant_id].get("networks")
            clients = osclients.Clients(user["endpoint"])
            manila_scenario = manila_utils.ManilaScenario(clients=clients)
            self.context["tenants"][tenant_id]["share_networks"] = []
            self.context["tenants"][tenant_id]["security_services"] = []
            data = {"name": manila_scenario._generate_random_name(
                prefix="rally_manila_share_network_")}

            def _setup_share_network(tenant_id, data):
                share_network = manila_scenario._create_share_network(**data)
                self.context["tenants"][tenant_id][
                    "share_networks"].append(share_network)
                if self.config["use_security_services"]:
                    for ss in self.config["security_services"]:
                        inst = manila_scenario._create_security_service(**ss)
                        self.context["tenants"][tenant_id][
                            "security_services"].append(inst)
                        manila_scenario._add_security_service_to_share_network(
                            inst.id, inst.id)

            if networks:
                for network in networks:
                    if network.get("cidr"):
                        data["nova_net_id"] = network["id"]
                    elif network.get("subnets"):
                        data["neutron_net_id"] = network["id"]
                        data["neutron_subnet_id"] = network["subnets"][0]
                    else:
                        LOG.warning(_(
                            "Can not determine network service provider. "
                            "Share network will have no data."))
                    _setup_share_network(tenant_id, data)
            else:
                _setup_share_network(tenant_id, data)
            # NOTE(vponomaryov): create one infinite iterator over
            # share networks per tenant. It allows us to balance our shares
            # among share networks.
            self.context["tenants"][tenant_id]["sn_iterator"] = (
                itertools.cycle(
                    self.context["tenants"][tenant_id]["share_networks"]))

            # Create shares
            self._create_shares(
                manila_scenario,
                tenant_id,
                self.config["share_proto"],
                self.config["size"])

    def _create_shares(self, manila_scenario, tenant_id, share_proto, size=1):
        tenant_ctxt = self.context["tenants"][tenant_id]
        tenant_ctxt.setdefault("shares", list())
        for i in range(self.config["shares_per_tenant"]):
            kwargs = {"share_proto": share_proto, "size": size}
            kwargs["name"] = scenario_base.Scenario._generate_random_name(
                prefix="ctx_rally_share_")
            if tenant_ctxt.get("share_networks"):
                kwargs["share_network"] = next(tenant_ctxt["sn_iterator"])
            share = manila_scenario._create_share(**kwargs)
            tenant_ctxt["shares"].append(share)

    @utils.log_task_wrapper(LOG.info, _("Enter context: `manila`"))
    def setup(self):
        if not self.config["use_share_networks"]:
            for user, tenant_id in (utils.iterate_per_tenants(
                    self.context.get("users", []))):
                clients = osclients.Clients(user["endpoint"])
                manila_scenario = manila_utils.ManilaScenario(clients=clients)
                self._create_shares(
                    manila_scenario,
                    tenant_id,
                    self.config["share_proto"],
                    self.config["size"])
        elif self.context["config"].get("existing_users"):
            self._setup_for_existing_users()
        else:
            self._setup_for_autocreated_users()

    def _cleanup_tenant_resources(self, resources_plural_name,
                                  resources_singular_name):
        """Cleans up tenant resources.

        :param resources_plural_name: plural name for resources, should be
            one of "shares", "share_networks" or "security_services".
        :param resources_singular_name: singular name for resource. Expected
            to be part of resource deletion method name (obj._delete_%s)
        """
        for user, tenant_id in (utils.iterate_per_tenants(
                self.context.get("users", []))):
            clients = osclients.Clients(user["endpoint"])
            manila_scenario = manila_utils.ManilaScenario(clients=clients)
            resources = self.context["tenants"][tenant_id].get(
                resources_plural_name, [])
            for resource in resources:
                logger = log.ExceptionLogger(
                    LOG,
                    _("Failed to delete %(name)s %(id)s for tenant %(t)s.") % {
                        "id": resource, "t": tenant_id,
                        "name": resources_singular_name})
                with logger:
                    delete_func = getattr(
                        manila_scenario,
                        "_delete_%s" % resources_singular_name)
                    delete_func(resource)

    def _cleanup_tenant_shares(self):
        """Cleans up tenant shares."""
        self._cleanup_tenant_resources("shares", "share")

    def _cleanup_tenant_share_networks(self):
        """Cleans up tenant share networks."""
        self._cleanup_tenant_resources("share_networks", "share_network")

    def _cleanup_tenant_security_services(self):
        """Cleans up tenant security services."""
        self._cleanup_tenant_resources("security_services", "security_service")

    def _wait_for_cleanup_of_share_networks(self):
        """Waits for deletion of Manila service resources."""
        for user, tenant_id in (utils.iterate_per_tenants(
                self.context.get("users", []))):
            self._wait_for_resources_deletion(
                self.context["tenants"][tenant_id].get("shares"))

            clients = osclients.Clients(self.context["admin"]["endpoint"])
            manila_scenario = manila_utils.ManilaScenario(clients=clients)
            for sn in self.context["tenants"][tenant_id]["share_networks"]:
                share_servers = manila_scenario._list_share_servers(
                    search_opts={"share_network": sn.id})
                self._wait_for_resources_deletion(share_servers)

    def _wait_for_resources_deletion(self, resources):
        """Waiter for resources deletion.

        :param resources: resource or list of resources for deletion
            verification
        """
        if not resources:
            return
        if not isinstance(resources, list):
            resources = [resources]
        for resource in resources:
            bench_utils.wait_for_delete(
                resource,
                update_resource=bench_utils.get_from_manager(),
                timeout=CONF.benchmark.manila_share_delete_timeout,
                check_interval=(
                    CONF.benchmark.manila_share_delete_poll_interval))

    @utils.log_task_wrapper(LOG.info, _("Exit context: `manila`"))
    def cleanup(self):
        # NOTE(vponomaryov): delete shares that were created by context
        self._cleanup_tenant_shares()

        if not self.context.get("manila_delete_share_networks", True):
            # NOTE(vponomaryov): assume that share networks were not created
            # by test run.
            return
        else:
            # NOTE(vponomaryov): Schedule 'share networks' and
            # 'security services' deletions per each tenant.
            self._cleanup_tenant_share_networks()
            self._cleanup_tenant_security_services()

            # NOTE(vponomaryov): Share network deletion schedules deletion of
            # share servers. So, we should wait for its deletion too to avoid
            # further failures of network resources release.
            # Use separate cycle to make share servers be deleted in parallel.
            self._wait_for_cleanup_of_share_networks()
