"""
Immich Screensaver - Album/People Selector
Provides dialogs for selecting albums and people from Immich
"""

import os
import sys
import xbmc
import xbmcgui
import xbmcaddon

from resources.lib.immich_client import ImmichClient

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')


def load_config():
    """Load server_url and api_key from config.txt."""
    config_path = os.path.join(ADDON_PATH, 'config.txt')

    if not os.path.exists(config_path):
        xbmc.log(f"[screensaver.immich] selector: No config.txt at {config_path}", xbmc.LOGWARNING)
        return None, None

    server_url = None
    api_key = None

    try:
        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if key == 'server_url':
                        server_url = value
                    elif key == 'api_key':
                        api_key = value

        xbmc.log(f"[screensaver.immich] selector: Loaded config - server: {server_url[:20] if server_url else 'None'}...", xbmc.LOGINFO)
        return server_url, api_key
    except Exception as e:
        xbmc.log(f"[screensaver.immich] selector: Failed to load config: {e}", xbmc.LOGERROR)
        return None, None


def get_client():
    """Create and return an Immich client from config.txt."""
    server_url, api_key = load_config()

    if not server_url or not api_key:
        xbmcgui.Dialog().ok(
            'Immich Screensaver',
            'Please ensure config.txt contains server_url and api_key.'
        )
        return None

    client = ImmichClient(server_url, api_key)

    if not client.test_connection():
        xbmcgui.Dialog().ok(
            'Immich Screensaver',
            'Cannot connect to Immich server. Please check config.txt.'
        )
        return None

    return client


def select_album():
    """Show dialog to select an album."""
    client = get_client()
    if not client:
        return

    # Fetch all albums (both owned and shared)
    xbmcgui.Dialog().notification('Immich', 'Loading albums...', time=1000)

    owned_albums = client.get_all_albums(shared=False) or []
    shared_albums = client.get_all_albums(shared=True) or []

    # Combine and create list
    albums = []
    album_labels = []

    for album in owned_albums:
        albums.append(album)
        name = album.get('albumName', 'Unnamed')
        count = album.get('assetCount', 0)
        album_labels.append(f"{name} ({count} photos)")

    for album in shared_albums:
        # Avoid duplicates
        if album.get('id') not in [a.get('id') for a in owned_albums]:
            albums.append(album)
            name = album.get('albumName', 'Unnamed')
            count = album.get('assetCount', 0)
            owner = album.get('owner', {}).get('name', 'Unknown')
            album_labels.append(f"{name} ({count}) - shared by {owner}")

    if not albums:
        xbmcgui.Dialog().ok('Immich', 'No albums found.')
        return

    # Show selection dialog
    selected = xbmcgui.Dialog().select('Select Album', album_labels)

    if selected >= 0:
        album = albums[selected]
        album_id = album.get('id')
        album_name = album.get('albumName', 'Unnamed')

        # Save to settings
        ADDON.setSetting('album_id', album_id)
        ADDON.setSetting('album_name', album_name)

        xbmcgui.Dialog().notification(
            'Immich',
            f'Selected: {album_name}',
            xbmcgui.NOTIFICATION_INFO,
            2000
        )


def select_people():
    """Show dialog to select people (multiple selection)."""
    client = get_client()
    if not client:
        return

    # Fetch all people
    xbmcgui.Dialog().notification('Immich', 'Loading people...', time=1000)

    people = client.get_all_people() or []

    if not people:
        xbmcgui.Dialog().ok('Immich', 'No people found.')
        return

    # Create list with names
    people_labels = []
    for person in people:
        name = person.get('name', '')
        if name:
            people_labels.append(name)
        else:
            people_labels.append('Unknown Person')

    # Get currently selected people
    current_ids = ADDON.getSetting('people_ids') or ''
    current_id_list = [p.strip() for p in current_ids.split(',') if p.strip()]

    # Pre-select currently selected people
    preselect = []
    for i, person in enumerate(people):
        if person.get('id') in current_id_list:
            preselect.append(i)

    # Show multi-select dialog
    selected = xbmcgui.Dialog().multiselect(
        'Select People (multiple allowed)',
        people_labels,
        preselect=preselect
    )

    if selected is not None:  # User didn't cancel
        selected_ids = []
        selected_names = []

        for i in selected:
            person = people[i]
            selected_ids.append(person.get('id'))
            name = person.get('name', 'Unknown')
            selected_names.append(name)

        # Save to settings
        ADDON.setSetting('people_ids', ','.join(selected_ids))
        ADDON.setSetting('people_names', ', '.join(selected_names))

        if selected_names:
            xbmcgui.Dialog().notification(
                'Immich',
                f'Selected: {", ".join(selected_names[:3])}{"..." if len(selected_names) > 3 else ""}',
                xbmcgui.NOTIFICATION_INFO,
                2000
            )
        else:
            xbmcgui.Dialog().notification(
                'Immich',
                'No people selected',
                xbmcgui.NOTIFICATION_INFO,
                2000
            )


def clear_cache():
    """Clear the screensaver image cache."""
    server_url, api_key = load_config()

    if not server_url or not api_key:
        xbmcgui.Dialog().ok(
            'Immich Screensaver',
            'Please ensure config.txt is properly configured.'
        )
        return

    client = ImmichClient(server_url, api_key)

    # Get cache size before clearing
    size_before = client.get_cache_size()

    # Clear cache (files older than 0 days = all files)
    client.clear_cache(max_age_days=0)

    xbmcgui.Dialog().notification(
        'Immich Screensaver',
        f'Cleared {size_before:.1f} MB of cached images',
        xbmcgui.NOTIFICATION_INFO,
        3000
    )


def main():
    """Main entry point for selector script."""
    if len(sys.argv) < 2:
        return

    action = sys.argv[1]

    if action == 'select_album':
        select_album()
    elif action == 'select_people':
        select_people()
    elif action == 'clear_cache':
        clear_cache()


if __name__ == '__main__':
    main()
