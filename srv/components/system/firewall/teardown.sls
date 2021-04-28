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


# Ensure ssh works when the firwall service starts for the next time
Reset default zone:
  firewalld.present:
    - name: public
    - default: True
    - prune_ports: True
    - prune_services: False
    - prune_interfaces: False
    - services:
      - ssh
    - ports:
      - 4505/tcp
      - 4506/tcp
    - watch_in:
      - Delete firewall checkpoint flag

{#% if 'public-data-zone' in salt['firewalld.get_zones']() %#}
Remove public data interfaces:
  firewalld.present:
    - name: public-data-zone
    - prune_interfaces: True
    - watch_in:
      - Delete firewall checkpoint flag
    
Remove public-data-zone:
  module.run:
    - firewalld.delete_zone:
      - zone: public-data-zone
    - require:
      - Reset default zone
    - watch_in:
      - Delete firewall checkpoint flag
{#% endif %#}

{#% if 'management-zone' in salt['firewalld.get_zones']() %#}
Remove public management interfaces:
  firewalld.present:
    - name: management-zone
    - prune_interfaces: True
    - watch_in:
      - Delete firewall checkpoint flag

Remove management-zone:
  module.run:
    - firewalld.delete_zone:
      - zone: management-zone
    - require:
      - Reset default zone
    - watch_in:
      - Delete firewall checkpoint flag

{#% endif %#}

Remove private data interfaces:
  firewalld.present:
    - name: trusted
    - prune_interfaces: True
    - prune_sources: True
    - watch_in:
      - Delete firewall checkpoint flag

Delete firewall checkpoint flag:
  file.absent:
    - name: /opt/seagate/cortx_configs/provisioner_generated/{{ grains['id'] }}.firewall
    - contents: {{ grains['id'] }}.firewall

Refresh firewalld:
  module.run:
    - service.restart:
      - firewalld
    - watch_in:
      - Delete firewall checkpoint flag

# Restart salt-minion service:
#  cmd.run:
#    - name: 'systemctl restart salt-minion'
#    - bg: True
#    - require:
#      - Remove public management interfaces
#      - Remove management-zone
#      - Remove public data interfaces
#      - Remove public-data-zone
#      - Remove private data interfaces
#      - Refresh firewalld
