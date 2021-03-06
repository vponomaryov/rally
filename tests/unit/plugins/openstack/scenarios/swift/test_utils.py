# Copyright 2015: Cisco Systems, Inc.
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

import mock

from rally.plugins.openstack.scenarios.swift import utils
from tests.unit import test

SWIFT_UTILS = "rally.plugins.openstack.scenarios.swift.utils"


class SwiftScenarioTestCase(test.ClientsTestCase):

    def test__list_containers(self):
        headers_dict = mock.MagicMock()
        containers_list = mock.MagicMock()
        self.clients("swift").get_account.return_value = (headers_dict,
                                                          containers_list)
        scenario = utils.SwiftScenario()

        self.assertEqual((headers_dict, containers_list),
                         scenario._list_containers(fargs="f"))
        kw = {"full_listing": True, "fargs": "f"}
        self.clients("swift").get_account.assert_called_once_with(**kw)

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "swift.list_containers")

    def test__create_container(self):
        container_name = mock.MagicMock()
        scenario = utils.SwiftScenario()

        # name + public=True + kw
        self.assertEqual(container_name,
                         scenario._create_container(container_name,
                                                    public=True, fargs="f"))
        kw = {"headers": {"X-Container-Read": ".r:*,.rlistings"}, "fargs": "f"}
        self.clients("swift").put_container.assert_called_once_with(
            container_name,
            **kw)
        # name + public=True + additional header + kw
        self.clients("swift").put_container.reset_mock()
        self.assertEqual(container_name,
                         scenario._create_container(container_name,
                                                    public=True,
                                                    headers={"X-fake-name":
                                                             "fake-value"},
                                                    fargs="f"))
        kw = {"headers": {"X-Container-Read": ".r:*,.rlistings",
                          "X-fake-name": "fake-value"}, "fargs": "f"}
        self.clients("swift").put_container.assert_called_once_with(
            container_name,
            **kw)
        # name + public=False + additional header + kw
        self.clients("swift").put_container.reset_mock()
        self.assertEqual(container_name,
                         scenario._create_container(container_name,
                                                    public=False,
                                                    headers={"X-fake-name":
                                                             "fake-value"},
                                                    fargs="f"))
        kw = {"headers": {"X-fake-name": "fake-value"}, "fargs": "f"}
        self.clients("swift").put_container.assert_called_once_with(
            container_name,
            **kw)
        # name + kw
        self.clients("swift").put_container.reset_mock()
        self.assertEqual(container_name,
                         scenario._create_container(container_name, fargs="f"))
        kw = {"fargs": "f"}
        self.clients("swift").put_container.assert_called_once_with(
            container_name,
            **kw)
        # kw
        scenario._generate_random_name = mock.MagicMock(
            return_value=container_name)
        self.clients("swift").put_container.reset_mock()
        self.assertEqual(container_name,
                         scenario._create_container(fargs="f"))
        kw = {"fargs": "f"}
        self.clients("swift").put_container.assert_called_once_with(
            container_name,
            **kw)
        self.assertEqual(1, scenario._generate_random_name.call_count)

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "swift.create_container")

    def test__delete_container(self):
        container_name = mock.MagicMock()
        scenario = utils.SwiftScenario()
        scenario._delete_container(container_name, fargs="f")

        kw = {"fargs": "f"}
        self.clients("swift").delete_container.assert_called_once_with(
            container_name,
            **kw)

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "swift.delete_container")

    def test__list_objects(self):
        container_name = mock.MagicMock()
        headers_dict = mock.MagicMock()
        objects_list = mock.MagicMock()
        self.clients("swift").get_container.return_value = (headers_dict,
                                                            objects_list)
        scenario = utils.SwiftScenario()

        self.assertEqual((headers_dict, objects_list),
                         scenario._list_objects(container_name, fargs="f"))
        kw = {"full_listing": True, "fargs": "f"}
        self.clients("swift").get_container.assert_called_once_with(
            container_name,
            **kw)

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "swift.list_objects")

    def test__upload_object(self):
        container_name = mock.MagicMock()
        object_name = mock.MagicMock()
        content = mock.MagicMock()
        etag = mock.MagicMock()
        self.clients("swift").put_object.return_value = etag
        scenario = utils.SwiftScenario()

        # container + content + name + kw
        self.assertEqual((etag, object_name),
                         scenario._upload_object(container_name, content,
                                                 object_name=object_name,
                                                 fargs="f"))
        kw = {"fargs": "f"}
        self.clients("swift").put_object.assert_called_once_with(
            container_name, object_name,
            content, **kw)
        # container + content + kw
        scenario._generate_random_name = mock.MagicMock(
            return_value=object_name)
        self.clients("swift").put_object.reset_mock()
        self.assertEqual((etag, object_name),
                         scenario._upload_object(container_name, content,
                                                 fargs="f"))
        kw = {"fargs": "f"}
        self.clients("swift").put_object.assert_called_once_with(
            container_name, object_name,
            content, **kw)
        self.assertEqual(1, scenario._generate_random_name.call_count)

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "swift.upload_object")

    def test__download_object(self):
        container_name = mock.MagicMock()
        object_name = mock.MagicMock()
        headers_dict = mock.MagicMock()
        content = mock.MagicMock()
        self.clients("swift").get_object.return_value = (headers_dict, content)
        scenario = utils.SwiftScenario()

        self.assertEqual((headers_dict, content),
                         scenario._download_object(container_name, object_name,
                                                   fargs="f"))
        kw = {"fargs": "f"}
        self.clients("swift").get_object.assert_called_once_with(
            container_name, object_name,
            **kw)

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "swift.download_object")

    def test__delete_object(self):
        container_name = mock.MagicMock()
        object_name = mock.MagicMock()
        scenario = utils.SwiftScenario()
        scenario._delete_object(container_name, object_name, fargs="f")

        kw = {"fargs": "f"}
        self.clients("swift").delete_object.assert_called_once_with(
            container_name, object_name,
            **kw)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "swift.delete_object")
