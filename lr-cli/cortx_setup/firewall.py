import argparse
import logging

from provisioner.salt import local_minion_id, StatesApplier

logger = logging.getLogger(__name__)


class firewall():
    def configure_firewall():

        node_id = local_minion_id()

        print("configuring firewall")
        logger.info(f"Applying Hare post_update logic on {node_id}")
        # StatesApplier.apply(["components.system.firewall"], local_minion_id())
        StatesApplier.apply(
            ["components.system.firewall"],
            targets=node_id
        )


if __name__ == '__main__':
    firewall.configure_firewall()
