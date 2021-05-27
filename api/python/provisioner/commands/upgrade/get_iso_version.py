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
import logging
from typing import Type

from packaging import version
from provisioner import inputs
from provisioner.config import (CORTX_ISO_DIR, REPO_CANDIDATE_NAME,
                                SWUpgradeInfoFields)
from provisioner.pillar import PillarResolver, PillarKey

from provisioner.salt import local_minion_id, cmd_run
from provisioner.commands import CommandParserFillerMixin
from provisioner.vendor import attr

from .get_swupgrade_info import GetSWUpgradeInfo

from ...commands import GetReleaseVersion

from packaging import version

logger = logging.getLogger(__name__)


class GetISOVersion(CommandParserFillerMixin):
    """
    Base class that provides API for getting ISO Version information.
    """

    input_type: Type[inputs.NoParams] = inputs.NoParams

    def run(self, targets):
        #release_upgrade = GetSWUpgradeInfo()

        #release_current  = GetReleaseVersion()

        upgrade_data = GetSWUpgradeInfo()
        release_metadata = GetReleaseVersion()
        upgrade_ver = (
            f'{upgrade_data["metadata"][ReleaseInfo.VERSION.value]}-'
            f'{upgrade_data["metadata"][ReleaseInfo.BUILD.value]}'
        )
        release_ver = (
            f'{release_metadata[ReleaseInfo.VERSION.value]}-'
            f'{release_metadata[ReleaseInfo.BUILD.value]}'
        )
        release_ver = version.parse(release_ver)
        upgrade_ver = version.parse(upgrade_ver)
        if upgrade_ver > release_ver:
            return str(upgrade_ver)
        elif upgrade_ver == release_ver:
            return None
        else:  # upgrade_ver < release_ver
            raise ProvisionerError(
                "upgrade version is lower than currently installed one"
            )


