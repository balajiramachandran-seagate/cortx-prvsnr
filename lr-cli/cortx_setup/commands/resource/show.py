#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#


from ..command import Command


class ResourceShow(Command):
    _args = {
        'manefist': {
            'type': str,
            'default': None,
            'optional': True,
            'help': 'discover HW/SW Manifest for all resources'
        },
        'health': {
            'type': str,
            'default': None,
            'optional': True,
            'help': 'Health check for all the resources in the system'
        }
    }

    def run(self, manefist=None, health=None):
        if manefist:
            self.logger.info("discover HW/SW Manifest for all resources")
        if health:
            self.logger.info("Health check for all resources in the system")
        self.logger.info("Done")
