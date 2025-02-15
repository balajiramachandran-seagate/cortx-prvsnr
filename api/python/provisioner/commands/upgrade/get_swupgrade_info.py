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
from configparser import ConfigParser
from typing import Type
from urllib.parse import urlparse, unquote

from packaging import version

from provisioner import inputs
from provisioner.commands.upgrade.set_swupgrade_repo import CortxISOInfo, \
    SetSWUpgradeRepo
from provisioner.config import (CORTX_ISO_DIR, REPO_CANDIDATE_NAME,
                                RELEASE_INFO_FILE)
from provisioner.errors import SWUpdateRepoSourceError
from provisioner.pillar import PillarResolver, PillarKey

from provisioner.salt import local_minion_id
from provisioner.commands import CommandParserFillerMixin, commands
from provisioner.vendor import attr


logger = logging.getLogger(__name__)


@attr.s(auto_attribs=True)
class GetSWUpgradeInfoArgs:
    iso_path: str = attr.ib(
        metadata={
            inputs.METADATA_ARGPARSER: {
                'help': "Path to SW upgrade single ISO bundle"
            }
        },
        default=None
    )
    release: str = attr.ib(
        metadata={
            inputs.METADATA_ARGPARSER: {
                'help': "SW upgrade repository release version"
            }
        },
        default=None
    )


class GetSWUpgradeInfo(CommandParserFillerMixin):
    """
    Base class that provides API for getting SW upgrade repository information.

    """

    input_type: Type[inputs.NoParams] = inputs.NoParams
    _run_args_type = GetSWUpgradeInfoArgs

    @staticmethod
    def _get_set_swupgrade_repo_obj() -> SetSWUpgradeRepo:
        """
        Get SetSWUpgradeRepo instance

        Returns
        -------
        SetSWUpgradeRepo:
            return SetSWUpgradeRepo instance

        """
        # NOTE: get `SetSWUpgradeRepo` from list of commands since all
        #  objects are correctly defined (post- and pre- states)
        return commands['set_swupgrade_repo']

    def _get_repo_metadata(self, release: str) -> dict:
        """
        Load Cortx repository metadata for the given release

        Parameters
        ----------
        release : str
            SW upgrade repository version

        Returns
        -------
        dict:
            return dict with Cortx repository metadata

        """
        repo = f'sw_upgrade_{CORTX_ISO_DIR}_{release}'

        config = ConfigParser()
        config.read(f'/etc/yum.repos.d/{repo}.repo')
        repo_uri = config[repo].get('baseurl', None)

        if repo_uri is None:
            raise SWUpdateRepoSourceError(repo, 'baseurl is missed')

        res = urlparse(f'{repo_uri}/{RELEASE_INFO_FILE}')

        set_swupgrade_repo = self._get_set_swupgrade_repo_obj()

        return set_swupgrade_repo.load_metadata(
                    release_file_path=unquote(res.path),
                    remote=res.scheme != 'file')

    def run(self, iso_path: str = None, release: str = None) -> CortxISOInfo:
        """
        Main function for Get SW Upgrade Repo command. Command returns
        information about CORTX packages and their versions.

        Parameters
        ----------
        iso_path: str
            Path to SW upgrade single ISO bundle
        release: str
            SW upgrade repository release version

        Returns
        -------
        CortxISOInfo:
            return instance of CortxISOInfo with CORTX packages versions and
            Cortx repo metadata

        """
        local_minion = local_minion_id()
        set_swupgrade_repo = self._get_set_swupgrade_repo_obj()

        if iso_path is not None:
            # if the `iso_path` is set up, we ignore the `release` parameter
            return set_swupgrade_repo.run(iso_path, dry_run=True)

        if release is None:
            # NOTE: take the latest release from SW upgrade repositories

            # TODO: make get pillar API public and available for others to
            #  avoid code duplication
            pillar_path = 'release/upgrade/repos'
            pillars = PillarResolver(local_minion).get(
                [PillarKey(pillar_path)],
                fail_on_undefined=True
            )

            upgrade_releases = list(pillars[local_minion][
                PillarKey(pillar_path)].keys())

            upgrade_releases.remove(REPO_CANDIDATE_NAME)

            # NOTE: Assumption: we expect that SW Upgrade release version
            # is formatted according to PEP-440
            release = max(upgrade_releases, key=version.parse)

        packages = set_swupgrade_repo.get_packages_version(release)
        metadata = self._get_repo_metadata(release)

        return CortxISOInfo(packages=packages, metadata=metadata)
