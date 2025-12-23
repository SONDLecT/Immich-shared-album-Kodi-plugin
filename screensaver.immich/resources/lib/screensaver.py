"""
Immich Screensaver - Main screensaver logic
"""

import os
import random
from datetime import datetime

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
    IMAGE_CONTROL_1 = 100
    IMAGE_CONTROL_2 = 200
    INFO_OVERLAY = 300
    DATE_LABEL = 102
    LOCATION_LABEL = 103
    DESCRIPTION_LABEL = 101

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.addon = xbmcaddon.Addon()
        self.images = []
        self.is_active = True
        self.exit_monitor = None
        self.client = None
        self.current_image_control = 1  # Toggle between 1 and 2 for crossfade

    def onInit(self):
        """Called when the screensaver window is initialized."""
        # Set up exit monitor
        self.exit_monitor = ExitMonitor(self._exit_callback)

        # Load config file first and apply to settings if needed
        self._apply_config_file()

        # Load settings
        server_url = self.addon.getSetting('server_url')
        api_key = self.addon.getSetting('api_key')

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

        # Hide/show info overlay
        try:
            overlay = self.getControl(self.INFO_OVERLAY)
            overlay.setVisible(show_info)
        except RuntimeError:
            pass

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

            # Update display with crossfade
            self._display_image_crossfade(image_path, image_data, show_info)

            # Wait for next image
            if self.exit_monitor.waitForAbort(display_time):
                break

        self.close()

    def _apply_config_file(self):
        """Load configuration from config.txt and apply to addon settings."""
        addon_path = self.addon.getAddonInfo('path')
        config_path = os.path.join(addon_path, 'config.txt')

        if not os.path.exists(config_path):
            return

        try:
            with open(config_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('#') or not line or '=' not in line:
                        continue
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()

                    # Apply to addon settings if current setting is empty
                    if key == 'server_url':
                        if not self.addon.getSetting('server_url'):
                            self.addon.setSetting('server_url', value)
                    elif key == 'api_key':
                        if not self.addon.getSetting('api_key'):
                            self.addon.setSetting('api_key', value)
        except Exception as e:
            xbmc.log(f"[screensaver.immich] Error reading config: {e}", xbmc.LOGERROR)

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

    def _display_image_crossfade(self, image_path, image_data, show_info):
        """Display an image with crossfade effect."""
        # Determine which control to use for crossfade
        if self.current_image_control == 1:
            active_control_id = self.IMAGE_CONTROL_1
            self.current_image_control = 2
        else:
            active_control_id = self.IMAGE_CONTROL_2
            self.current_image_control = 1

        try:
            # Set image on the active control
            control = self.getControl(active_control_id)
            control.setImage(image_path)
        except RuntimeError as e:
            xbmc.log(f"[screensaver.immich] Error setting image: {e}", xbmc.LOGERROR)

        if show_info:
            self._update_info_labels(image_data)

    def _update_info_labels(self, image_data):
        """Update the info labels with photo metadata."""
        # Get metadata
        created_at = image_data.get('fileCreatedAt', '') or image_data.get('createdAt', '')
        exif = image_data.get('exifInfo', {}) or {}

        # Format date nicely
        date_str = self._format_date(created_at)

        # Get location from EXIF
        location_str = self._format_location(exif)

        # Get camera/description info
        description_str = self._format_description(image_data, exif)

        # Update labels
        try:
            self.getControl(self.DATE_LABEL).setLabel(date_str)
        except RuntimeError:
            pass

        try:
            self.getControl(self.LOCATION_LABEL).setLabel(location_str)
        except RuntimeError:
            pass

        try:
            self.getControl(self.DESCRIPTION_LABEL).setLabel(description_str)
        except RuntimeError:
            pass

    def _format_date(self, date_string):
        """Format date string nicely."""
        if not date_string:
            return ''

        try:
            # Parse ISO format date
            if 'T' in date_string:
                dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            else:
                dt = datetime.strptime(date_string[:10], '%Y-%m-%d')

            # Format nicely: "Saturday, December 23, 2025"
            return dt.strftime('%A, %B %d, %Y')
        except (ValueError, TypeError):
            # Fallback to just the date portion
            return date_string[:10] if len(date_string) >= 10 else date_string

    def _format_location(self, exif):
        """Format location from EXIF data."""
        city = exif.get('city', '')
        state = exif.get('state', '')
        country = exif.get('country', '')

        # Build location string
        location_parts = [p for p in [city, state, country] if p]
        if location_parts:
            return ', '.join(location_parts)
        return ''

    def _format_description(self, image_data, exif):
        """Format description/camera info."""
        # Try to get description first
        description = image_data.get('description', '')
        if description:
            return description

        # Otherwise show camera info
        make = exif.get('make', '')
        model = exif.get('model', '')

        if make and model:
            # Clean up model name (often includes make)
            if make.lower() in model.lower():
                return model
            return f"{make} {model}"
        elif model:
            return model
        elif make:
            return make

        return ''

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
