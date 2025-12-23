"""
Immich Kodi Plugin - Main Entry Point
Browse your Immich photo library directly in Kodi
"""

import os
import sys
import shutil
import urllib.parse

import xbmc
import xbmcgui
import xbmcvfs
import xbmcaddon

# Get addon info (always available)
ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_PATH = ADDON.getAddonInfo('path')


def clear_cache():
    """Clear the image cache directory."""
    cache_dir = os.path.join(
        xbmcvfs.translatePath(ADDON.getAddonInfo('profile')),
        'cache'
    )

    if os.path.exists(cache_dir):
        try:
            # Count files before deletion
            file_count = len([f for f in os.listdir(cache_dir) if os.path.isfile(os.path.join(cache_dir, f))])

            # Calculate size
            total_size = sum(
                os.path.getsize(os.path.join(cache_dir, f))
                for f in os.listdir(cache_dir)
                if os.path.isfile(os.path.join(cache_dir, f))
            )
            size_mb = total_size / (1024 * 1024)

            # Delete cache directory
            shutil.rmtree(cache_dir)
            os.makedirs(cache_dir)

            xbmcgui.Dialog().notification(
                ADDON_NAME,
                f'Cleared {file_count} files ({size_mb:.1f} MB)',
                xbmcgui.NOTIFICATION_INFO,
                3000
            )
            xbmc.log(f'[{ADDON_ID}] Cache cleared: {file_count} files, {size_mb:.1f} MB', xbmc.LOGINFO)
        except Exception as e:
            xbmcgui.Dialog().notification(
                ADDON_NAME,
                'Failed to clear cache',
                xbmcgui.NOTIFICATION_ERROR,
                3000
            )
            xbmc.log(f'[{ADDON_ID}] Failed to clear cache: {e}', xbmc.LOGERROR)
    else:
        xbmcgui.Dialog().notification(
            ADDON_NAME,
            'Cache is already empty',
            xbmcgui.NOTIFICATION_INFO,
            2000
        )


def get_params():
    """Parse query string parameters from the plugin URL."""
    params = {}
    if len(sys.argv) > 2 and sys.argv[2]:
        query = sys.argv[2].lstrip('?')
        params = dict(urllib.parse.parse_qsl(query))
    return params


def load_config_file():
    """
    Load settings from config.txt if it exists.
    This allows pre-configuring the addon before installation.

    Config file format (one per line):
        server_url=https://immich.example.com
        api_key=your-api-key-here
    """
    config_path = os.path.join(ADDON_PATH, 'config.txt')
    if not os.path.exists(config_path):
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
        if 'api_key' in config:
            ADDON.setSetting('api_key', config['api_key'])

        xbmc.log(f'[{ADDON_ID}] Loaded settings from config.txt', xbmc.LOGINFO)
        return True
    except Exception as e:
        xbmc.log(f'[{ADDON_ID}] Failed to load config.txt: {e}', xbmc.LOGERROR)
        return False


def run_plugin():
    """Run the main plugin UI."""
    import xbmcplugin
    from resources.lib.immich_client import ImmichClient
    from resources.lib.plugin import ImmichPlugin

    HANDLE = int(sys.argv[1])
    BASE_URL = sys.argv[0]

    params = get_params()
    action = params.get('action', 'main_menu')

    # Get settings
    server_url = ADDON.getSetting('server_url')
    api_key = ADDON.getSetting('api_key')

    # Try loading from config file if settings are empty
    if not server_url or not api_key:
        if load_config_file():
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


def main():
    """Main entry point - handles both plugin and script modes."""
    # Check if running as a script (from settings action)
    if len(sys.argv) > 1 and sys.argv[1] == 'clear_cache':
        clear_cache()
        return

    # Otherwise run as plugin
    run_plugin()


if __name__ == '__main__':
    main()
