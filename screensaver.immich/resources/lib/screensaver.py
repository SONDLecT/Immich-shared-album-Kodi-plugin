"""
Immich Screensaver - Main screensaver logic
"""

import os
import random

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

from resources.lib.immich_client import ImmichClient


class ExitMonitor(xbmc.Monitor):
    """Monitor for screensaver exit events."""

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def onScreensaverDeactivated(self):
        self.callback()


class ImmichScreensaver(xbmcgui.WindowXMLDialog):
    """Immich photo screensaver for Kodi."""

    # Control IDs from XML
    BACKGROUND_IMAGE = 100
    IMAGE_LABEL = 101
    DATE_LABEL = 102
    LOCATION_LABEL = 103

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.addon = xbmcaddon.Addon()
        self.images = []
        self.is_active = True
        self.exit_monitor = None
        self.client = None

    def onInit(self):
        """Called when the screensaver window is initialized."""
        # Set up exit monitor
        self.exit_monitor = ExitMonitor(self._exit_callback)

        # Load settings
        server_url = self.addon.getSetting('server_url')
        api_key = self.addon.getSetting('api_key')

        # Check for config file if settings are empty
        if not server_url or not api_key:
            server_url, api_key = self._load_config_file()

        if not server_url or not api_key:
            self._show_error("Please configure Immich server settings")
            self.close()
            return

        # Initialize client
        self.client = ImmichClient(server_url, api_key)

        # Test connection
        if not self.client.test_connection():
            self._show_error("Cannot connect to Immich server")
            self.close()
            return

        # Load images based on settings
        self._load_images()

        if not self.images:
            self._show_error("No images found")
            self.close()
            return

        # Get display settings
        try:
            display_time = int(self.addon.getSetting('display_time') or '10')
        except ValueError:
            display_time = 10

        show_info = self.addon.getSetting('show_info') == 'true'

        # Main screensaver loop
        while self.is_active and not self.exit_monitor.abortRequested():
            if not self.images:
                self._load_images()
                if not self.images:
                    break

            # Pick random image
            image_data = random.choice(self.images)
            self.images.remove(image_data)

            # Download and display image
            image_path = self._get_image_path(image_data)
            if not image_path:
                continue

            # Update display
            self._display_image(image_path, image_data, show_info)

            # Wait for next image
            if self.exit_monitor.waitForAbort(display_time):
                break

        self.close()

    def _load_config_file(self):
        """Load configuration from config.txt file."""
        addon_path = self.addon.getAddonInfo('path')
        config_path = os.path.join(addon_path, 'config.txt')

        if not os.path.exists(config_path):
            return None, None

        server_url = None
        api_key = None

        try:
            with open(config_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('#') or '=' not in line:
                        continue
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if key == 'server_url':
                        server_url = value
                    elif key == 'api_key':
                        api_key = value
        except Exception as e:
            xbmc.log(f"[screensaver.immich] Error reading config: {e}", xbmc.LOGERROR)

        return server_url, api_key

    def _load_images(self):
        """Load images based on current settings."""
        source_mode = self.addon.getSetting('source_mode') or '0'
        self.images = []

        if source_mode == '0':
            # Random from all photos
            self._load_random_images()
        elif source_mode == '1':
            # Specific album
            album_id = self.addon.getSetting('album_id')
            if album_id:
                self._load_album_images(album_id)
            else:
                self._load_random_images()
        elif source_mode == '2':
            # Shared albums
            self._load_shared_album_images()
        elif source_mode == '3':
            # Specific people
            people_ids = self.addon.getSetting('people_ids')
            if people_ids:
                self._load_people_images(people_ids)
            else:
                self._load_random_images()
        elif source_mode == '4':
            # Favorites
            self._load_favorites()

        # Shuffle the images
        random.shuffle(self.images)
        xbmc.log(f"[screensaver.immich] Loaded {len(self.images)} images", xbmc.LOGINFO)

    def _load_random_images(self):
        """Load random images from the library."""
        # Use search to get random images
        result = self.client.search_random(count=100)
        if result:
            self.images = [img for img in result if img.get('type') == 'IMAGE']

    def _load_album_images(self, album_id):
        """Load images from a specific album."""
        album = self.client.get_album(album_id)
        if album and 'assets' in album:
            self.images = [a for a in album['assets'] if a.get('type') == 'IMAGE']

    def _load_shared_album_images(self):
        """Load images from all shared albums."""
        albums = self.client.get_all_albums(shared=True)
        for album in albums:
            album_data = self.client.get_album(album.get('id'))
            if album_data and 'assets' in album_data:
                self.images.extend([a for a in album_data['assets'] if a.get('type') == 'IMAGE'])

    def _load_people_images(self, people_ids_str):
        """Load images featuring specific people."""
        # people_ids is a comma-separated string
        people_ids = [p.strip() for p in people_ids_str.split(',') if p.strip()]
        for person_id in people_ids:
            assets = self.client.get_person_assets(person_id, count=50)
            self.images.extend([a for a in assets if a.get('type') == 'IMAGE'])

    def _load_favorites(self):
        """Load favorite images."""
        assets = self.client.get_favorites(count=100)
        self.images = [a for a in assets if a.get('type') == 'IMAGE']

    def _get_image_path(self, image_data):
        """Download image and return local path."""
        asset_id = image_data.get('id')
        if not asset_id:
            return None
        return self.client.get_asset_original(asset_id)

    def _display_image(self, image_path, image_data, show_info):
        """Display an image on the screensaver."""
        # Set background image
        background = self.getControl(self.BACKGROUND_IMAGE)
        background.setImage(image_path)

        if show_info:
            # Set image info labels
            filename = image_data.get('originalFileName', '')
            created_at = image_data.get('fileCreatedAt', '')
            exif = image_data.get('exifInfo', {}) or {}

            # Format date
            date_str = ''
            if created_at:
                date_str = created_at[:10]  # YYYY-MM-DD

            # Get location from EXIF
            location_str = ''
            city = exif.get('city', '')
            state = exif.get('state', '')
            country = exif.get('country', '')
            location_parts = [p for p in [city, state, country] if p]
            if location_parts:
                location_str = ', '.join(location_parts)

            # Update labels (with error handling for missing controls)
            try:
                label = self.getControl(self.IMAGE_LABEL)
                label.setLabel(filename)
            except RuntimeError:
                pass

            try:
                date_label = self.getControl(self.DATE_LABEL)
                date_label.setLabel(date_str)
            except RuntimeError:
                pass

            try:
                location_label = self.getControl(self.LOCATION_LABEL)
                location_label.setLabel(location_str)
            except RuntimeError:
                pass
        else:
            # Hide info labels
            try:
                self.getControl(self.IMAGE_LABEL).setLabel('')
                self.getControl(self.DATE_LABEL).setLabel('')
                self.getControl(self.LOCATION_LABEL).setLabel('')
            except RuntimeError:
                pass

    def _show_error(self, message):
        """Show error notification."""
        xbmcgui.Dialog().notification(
            'Immich Screensaver',
            message,
            xbmcgui.NOTIFICATION_ERROR,
            5000
        )

    def _exit_callback(self):
        """Called when screensaver should exit."""
        self.is_active = False

    def onAction(self, action):
        """Handle user input to exit screensaver."""
        self.is_active = False
        self.close()
