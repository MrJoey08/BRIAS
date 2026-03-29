"""
BRIAS — Admin instellingen.

Opgeslagen als JSON in network_state/admin_config.json.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent.parent / "network_state" / "admin_config.json"

DEFAULTS = {
    "brias_active": True,          # reageert ze überhaupt?
    "allow_new_users": True,       # mogen nieuwe mensen zich registreren?
    "silent_mode": False,          # gebruikers kunnen inloggen maar BRIAS zwijgt
    "maintenance_message": "",     # bericht dat getoond wordt in silent mode
}


def load() -> dict:
    if CONFIG_PATH.exists():
        try:
            return {**DEFAULTS, **json.loads(CONFIG_PATH.read_text())}
        except Exception:
            pass
    return dict(DEFAULTS)


def save(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    merged = {**DEFAULTS, **config}
    CONFIG_PATH.write_text(json.dumps(merged, indent=2))
