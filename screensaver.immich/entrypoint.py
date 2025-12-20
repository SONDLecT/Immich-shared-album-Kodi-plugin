"""
Immich Screensaver for Kodi
Entry point for the screensaver addon
"""

import xbmcaddon

from resources.lib.screensaver import ImmichScreensaver

PATH = xbmcaddon.Addon().getAddonInfo("path")

if __name__ == "__main__":
    screensaver = ImmichScreensaver(
        "screensaver-immich.xml",
        PATH,
        "default",
        ""
    )
    screensaver.doModal()
    del screensaver
