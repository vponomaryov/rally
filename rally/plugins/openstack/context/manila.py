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
        },
        "additionalProperties": False
    }
    DEFAULT_CONFIG = {
        "use_share_networks": True,
        "share_networks": {},
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

    @utils.log_task_wrapper(LOG.info, _("Enter context: `manila`"))
    def setup(self):
        if not self.config["use_share_networks"]:
            return
        elif self.context["config"].get("existing_users"):
            self._setup_for_existing_users()
        else:
            # TODO(vponomaryov): add support of autocreated resources
            pass

    @utils.log_task_wrapper(LOG.info, _("Exit context: `manila`"))
    def cleanup(self):
        # TODO(vponomaryov): add cleanup for autocreated resources when appear.
        return
