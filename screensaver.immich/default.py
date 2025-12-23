"""
Immich Screensaver for Kodi
Entry point for the screensaver addon

Handles both screensaver mode and settings script mode.
"""

import os
import sys
import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')


def load_config_file():
    """
    Load settings from config.txt if it exists.
    This allows pre-configuring the addon before installation.
    """
    config_path = os.path.join(ADDON_PATH, 'config.txt')

    if not os.path.exists(config_path):
        xbmc.log(f"[screensaver.immich] No config.txt at {config_path}", xbmc.LOGINFO)
        return False

    try:
        config = {}
        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()

        # Save to Kodi settings if found
        if 'server_url' in config:
            ADDON.setSetting('server_url', config['server_url'])
            xbmc.log("[screensaver.immich] Set server_url from config.txt", xbmc.LOGINFO)
        if 'api_key' in config:
            ADDON.setSetting('api_key', config['api_key'])
            xbmc.log("[screensaver.immich] Set api_key from config.txt", xbmc.LOGINFO)

        return True
    except Exception as e:
        xbmc.log(f"[screensaver.immich] Failed to load config.txt: {e}", xbmc.LOGERROR)
        return False


# Always try to load config on addon access
server_url = ADDON.getSetting('server_url')
api_key = ADDON.getSetting('api_key')

if not server_url or not api_key:
    load_config_file()


# Check if we're running as a script (for settings actions) or as screensaver
if len(sys.argv) > 1:
    # Script mode - handle settings actions
    from resources.lib.selector import main
    main()
else:
    # Screensaver mode
    from resources.lib.screensaver import ImmichScreensaver

    screensaver = ImmichScreensaver(
        "screensaver-immich.xml",
        ADDON_PATH,
        "default",
        ""
    )
    screensaver.doModal()
    del screensaver
