"""
Immich Kodi Plugin - Main Entry Point
Browse your Immich photo library directly in Kodi
"""

import sys
import urllib.parse

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

from resources.lib.immich_client import ImmichClient
from resources.lib.plugin import ImmichPlugin

# Get addon handle and base URL
ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]


def get_params():
    """Parse query string parameters from the plugin URL."""
    params = {}
    if len(sys.argv) > 2 and sys.argv[2]:
        query = sys.argv[2].lstrip('?')
        params = dict(urllib.parse.parse_qsl(query))
    return params


def main():
    """Main entry point for the plugin."""
    params = get_params()
    action = params.get('action', 'main_menu')

    # Get settings
    server_url = ADDON.getSetting('server_url')
    api_key = ADDON.getSetting('api_key')

    # Check if settings are configured
    if not server_url or not api_key:
        xbmcgui.Dialog().ok(
            ADDON_NAME,
            'Please configure your Immich server URL and API key in the addon settings.'
        )
        ADDON.openSettings()
        return

    # Initialize the Immich client and plugin
    client = ImmichClient(server_url, api_key)
    plugin = ImmichPlugin(HANDLE, BASE_URL, ADDON, client)

    # Route to appropriate action
    if action == 'main_menu':
        plugin.show_main_menu()
    elif action == 'albums':
        plugin.show_albums()
    elif action == 'shared_albums':
        plugin.show_shared_albums()
    elif action == 'album':
        album_id = params.get('album_id')
        plugin.show_album_contents(album_id)
    elif action == 'shared_link':
        link_key = params.get('link_key')
        plugin.show_shared_link_contents(link_key)
    elif action == 'shared_links':
        plugin.show_shared_links()
    elif action == 'favorites':
        plugin.show_favorites()
    elif action == 'people':
        plugin.show_people()
    elif action == 'person':
        person_id = params.get('person_id')
        plugin.show_person_photos(person_id)
    elif action == 'person_slideshow':
        person_id = params.get('person_id')
        plugin.start_person_slideshow(person_id)
    elif action == 'timeline':
        plugin.show_timeline()
    elif action == 'timeline_bucket':
        bucket = params.get('bucket')
        plugin.show_timeline_bucket(bucket)
    elif action == 'view_image':
        asset_id = params.get('asset_id')
        plugin.view_image(asset_id)
    elif action == 'play_video':
        asset_id = params.get('asset_id')
        plugin.play_video(asset_id)
    elif action == 'slideshow':
        album_id = params.get('album_id')
        plugin.start_slideshow(album_id)
    elif action == 'search':
        plugin.search()
    else:
        xbmc.log(f'[{ADDON_ID}] Unknown action: {action}', xbmc.LOGWARNING)
        plugin.show_main_menu()


if __name__ == '__main__':
    main()
