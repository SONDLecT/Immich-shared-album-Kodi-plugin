"""
Immich Screensaver for Kodi
Entry point for the screensaver addon

Handles both screensaver mode and settings script mode.
"""

import sys
import xbmcaddon

# Check if we're running as a script (for settings actions) or as screensaver
if len(sys.argv) > 1:
    # Script mode - handle settings actions
    from resources.lib.selector import main
    main()
else:
    # Screensaver mode
    from resources.lib.screensaver import ImmichScreensaver

    PATH = xbmcaddon.Addon().getAddonInfo("path")

    screensaver = ImmichScreensaver(
        "screensaver-immich.xml",
        PATH,
        "default",
        ""
    )
    screensaver.doModal()
    del screensaver
