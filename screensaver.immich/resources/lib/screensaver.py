"""
Immich Screensaver - Main screensaver logic
"""

import os
import random
import threading
import time
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


class ImagePreloader:
    """Background pre-loader for images."""

    def __init__(self, client, count=3):
        self.client = client
        self.count = count
        self.preloaded = {}
        self.lock = threading.Lock()

    def preload(self, images):
        """Start pre-loading the next few images in background."""
        to_preload = images[:self.count]

        for image_data in to_preload:
            asset_id = image_data.get('id')
            if not asset_id:
                continue

            with self.lock:
                if asset_id in self.preloaded:
                    continue

            thread = threading.Thread(
                target=self._preload_image,
                args=(image_data,),
                daemon=True
            )
            thread.start()

    def _preload_image(self, image_data):
        """Download an image in background."""
        asset_id = image_data.get('id')
        if not asset_id:
            return

        try:
            path = self.client.get_asset_original(asset_id)
            if path:
                with self.lock:
                    self.preloaded[asset_id] = path
                xbmc.log(f"[screensaver.immich] Preloaded: {asset_id}", xbmc.LOGDEBUG)
        except Exception as e:
            xbmc.log(f"[screensaver.immich] Preload failed: {e}", xbmc.LOGERROR)

    def get_preloaded(self, asset_id):
        """Get preloaded path if available."""
        with self.lock:
            return self.preloaded.get(asset_id)

    def clear(self, asset_id):
        """Remove from preloaded cache after use."""
        with self.lock:
            self.preloaded.pop(asset_id, None)


class ImmichScreensaver(xbmcgui.WindowXMLDialog):
    """Immich photo screensaver for Kodi."""

    # Control IDs from XML
    IMAGE_CONTROL_1 = 101  # Primary image control
    IMAGE_CONTROL_2 = 102  # Secondary image control for crossfade
    INFO_OVERLAY = 300
    DATE_LABEL = 201
    LOCATION_LABEL = 202
    DESCRIPTION_LABEL = 203

    # Transition modes
    TRANSITION_NONE = '0'
    TRANSITION_FADE = '1'
    TRANSITION_KENBURNS = '2'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.addon = xbmcaddon.Addon()
        self.images = []
        self.is_active = True
        self.exit_monitor = None
        self.client = None
        self.preloader = None
        self.current_control = 1  # Tracks which control is showing (1 or 2)

    def onInit(self):
        """Called when the screensaver window is initialized."""
        xbmc.log("[screensaver.immich] onInit called", xbmc.LOGINFO)
        self.exit_monitor = ExitMonitor(self._exit_callback)

        # Apply config file settings
        self._apply_config_file()

        # Load settings
        server_url = self.addon.getSetting('server_url')
        api_key = self.addon.getSetting('api_key')

        xbmc.log(f"[screensaver.immich] Server URL: {server_url[:30] if server_url else 'NOT SET'}...", xbmc.LOGINFO)
        xbmc.log(f"[screensaver.immich] API Key: {'SET' if api_key else 'NOT SET'}", xbmc.LOGINFO)

        if not server_url or not api_key:
            self._show_error("Please configure Immich server settings")
            self.close()
            return

        # Initialize client
        self.client = ImmichClient(server_url, api_key)

        if not self.client.test_connection():
            self._show_error("Cannot connect to Immich server")
            self.close()
            return

        # Initialize preloader
        enable_cache = self.addon.getSetting('enable_cache') != 'false'
        if enable_cache:
            try:
                preload_count = int(self.addon.getSetting('preload_count') or '3')
            except ValueError:
                preload_count = 3
            self.preloader = ImagePreloader(self.client, preload_count)

        # Load images
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
        transition_mode = self.addon.getSetting('transition_mode') or self.TRANSITION_FADE

        xbmc.log(f"[screensaver.immich] Display time: {display_time}s, Show info: {show_info}, Transition: {transition_mode}", xbmc.LOGINFO)

        # Configure info overlay visibility
        self._set_info_visibility(show_info)

        # Start preloading
        if self.preloader:
            self.preloader.preload(self.images[:5])

        # Main loop
        xbmc.log(f"[screensaver.immich] Starting main loop with {len(self.images)} images", xbmc.LOGINFO)

        while self.is_active and not self.exit_monitor.abortRequested():
            if not self.images:
                self._load_images()
                if not self.images:
                    break

            image_data = self.images.pop(0)
            image_path = self._get_image_path(image_data)

            if not image_path:
                xbmc.log("[screensaver.immich] No image path returned, skipping", xbmc.LOGWARNING)
                continue

            if not os.path.exists(image_path):
                xbmc.log(f"[screensaver.immich] Image file does not exist: {image_path}", xbmc.LOGERROR)
                continue

            xbmc.log(f"[screensaver.immich] Displaying: {image_path}", xbmc.LOGINFO)

            # Preload next images
            if self.preloader:
                self.preloader.preload(self.images[:5])

            # Display image with transition
            self._display_image_with_transition(image_path, image_data, show_info, transition_mode, display_time)

            # Clear from preloader
            if self.preloader:
                self.preloader.clear(image_data.get('id'))

            # Wait (subtract transition time already spent)
            remaining_time = max(1, display_time - 2)  # Account for transition time
            if self.exit_monitor.waitForAbort(remaining_time):
                break

        self.close()

    def _set_info_visibility(self, visible):
        """Set visibility of info overlay and labels."""
        try:
            overlay = self.getControl(self.INFO_OVERLAY)
            overlay.setVisible(visible)
        except RuntimeError:
            pass

        for label_id in [self.DATE_LABEL, self.LOCATION_LABEL, self.DESCRIPTION_LABEL]:
            try:
                label = self.getControl(label_id)
                label.setVisible(visible)
            except RuntimeError:
                pass

    def _apply_config_file(self):
        """Load config from config.txt and apply to settings."""
        # Check multiple locations for config.txt
        addon_path = self.addon.getAddonInfo('path')
        profile_path = xbmcvfs.translatePath(self.addon.getAddonInfo('profile'))

        xbmc.log(f"[screensaver.immich] Addon path: {addon_path}", xbmc.LOGINFO)
        xbmc.log(f"[screensaver.immich] Profile path: {profile_path}", xbmc.LOGINFO)

        config_locations = [
            os.path.join(addon_path, 'config.txt'),
            os.path.join(profile_path, 'config.txt'),
        ]

        config_path = None
        for path in config_locations:
            xbmc.log(f"[screensaver.immich] Checking for config at: {path}", xbmc.LOGINFO)
            if os.path.exists(path):
                config_path = path
                xbmc.log(f"[screensaver.immich] Found config at: {path}", xbmc.LOGINFO)
                break

        if not config_path:
            xbmc.log("[screensaver.immich] No config.txt found in any location", xbmc.LOGINFO)
            return

        try:
            with open(config_path, 'r') as f:
                content = f.read()
                xbmc.log(f"[screensaver.immich] Config file content length: {len(content)}", xbmc.LOGINFO)

            with open(config_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('#') or not line or '=' not in line:
                        continue
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()

                    xbmc.log(f"[screensaver.immich] Config: {key}={value[:20] if value else 'EMPTY'}...", xbmc.LOGINFO)

                    if key == 'server_url' and value:
                        current = self.addon.getSetting('server_url')
                        xbmc.log(f"[screensaver.immich] Current server_url: '{current}'", xbmc.LOGINFO)
                        if not current:
                            self.addon.setSetting('server_url', value)
                            xbmc.log(f"[screensaver.immich] Set server_url from config", xbmc.LOGINFO)
                        else:
                            xbmc.log(f"[screensaver.immich] server_url already set, not overwriting", xbmc.LOGINFO)
                    elif key == 'api_key' and value:
                        current = self.addon.getSetting('api_key')
                        xbmc.log(f"[screensaver.immich] Current api_key: {'SET' if current else 'NOT SET'}", xbmc.LOGINFO)
                        if not current:
                            self.addon.setSetting('api_key', value)
                            xbmc.log(f"[screensaver.immich] Set api_key from config", xbmc.LOGINFO)
                        else:
                            xbmc.log(f"[screensaver.immich] api_key already set, not overwriting", xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"[screensaver.immich] Error reading config: {e}", xbmc.LOGERROR)

    def _load_images(self):
        """Load images based on settings."""
        source_mode = self.addon.getSetting('source_mode') or '0'
        self.images = []

        xbmc.log(f"[screensaver.immich] Loading images, source_mode={source_mode}", xbmc.LOGINFO)

        if source_mode == '0':
            self._load_random_images()
        elif source_mode == '1':
            album_id = self.addon.getSetting('album_id')
            if album_id:
                self._load_album_images(album_id)
            else:
                self._load_random_images()
        elif source_mode == '2':
            self._load_shared_album_images()
        elif source_mode == '3':
            people_ids = self.addon.getSetting('people_ids')
            if people_ids:
                self._load_people_images(people_ids)
            else:
                self._load_random_images()
        elif source_mode == '4':
            self._load_favorites()
        elif source_mode == '5':
            self._load_recent_images()
        elif source_mode == '6':
            self._load_memories()

        random.shuffle(self.images)
        xbmc.log(f"[screensaver.immich] Loaded {len(self.images)} images", xbmc.LOGINFO)

    def _load_random_images(self):
        result = self.client.search_random(count=100)
        if result:
            self.images = [img for img in result if img.get('type') == 'IMAGE']

    def _load_album_images(self, album_id):
        album = self.client.get_album(album_id)
        if album and 'assets' in album:
            self.images = [a for a in album['assets'] if a.get('type') == 'IMAGE']

    def _load_shared_album_images(self):
        albums = self.client.get_all_albums(shared=True)
        for album in albums:
            album_data = self.client.get_album(album.get('id'))
            if album_data and 'assets' in album_data:
                self.images.extend([a for a in album_data['assets'] if a.get('type') == 'IMAGE'])

    def _load_people_images(self, people_ids_str):
        people_ids = [p.strip() for p in people_ids_str.split(',') if p.strip()]
        for person_id in people_ids:
            assets = self.client.get_person_assets(person_id, count=50)
            self.images.extend([a for a in assets if a.get('type') == 'IMAGE'])

    def _load_favorites(self):
        assets = self.client.get_favorites(count=100)
        self.images = [a for a in assets if a.get('type') == 'IMAGE']

    def _load_recent_images(self):
        assets = self.client.search_recent(count=100, months=6)
        self.images = [a for a in assets if a.get('type') == 'IMAGE']

        # Weight by recency
        if self.images:
            weighted = []
            now = datetime.now()
            for img in self.images:
                created = img.get('fileCreatedAt', '')
                weight = 1
                if created:
                    try:
                        dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        days = (now - dt.replace(tzinfo=None)).days
                        weight = max(1, int(10 * (1 - days / 180)))
                    except (ValueError, TypeError):
                        pass
                weighted.extend([img] * weight)
            self.images = weighted

    def _load_memories(self):
        assets = self.client.get_memories()
        self.images = [a for a in assets if a.get('type') == 'IMAGE']
        if not self.images:
            xbmc.log("[screensaver.immich] No memories, falling back to recent", xbmc.LOGINFO)
            self._load_recent_images()

    def _get_image_path(self, image_data):
        """Get image path, checking preloader first."""
        asset_id = image_data.get('id')
        if not asset_id:
            return None

        if self.preloader:
            path = self.preloader.get_preloaded(asset_id)
            if path and os.path.exists(path):
                xbmc.log(f"[screensaver.immich] Using preloaded: {path}", xbmc.LOGDEBUG)
                return path

        path = self.client.get_asset_original(asset_id)
        xbmc.log(f"[screensaver.immich] Downloaded: {path}", xbmc.LOGDEBUG)
        return path

    def _display_image_with_transition(self, image_path, image_data, show_info, transition_mode, display_time):
        """Display image with the selected transition effect."""
        if transition_mode == self.TRANSITION_NONE:
            self._display_image_simple(image_path)
        elif transition_mode == self.TRANSITION_FADE:
            self._display_image_crossfade(image_path)
        elif transition_mode == self.TRANSITION_KENBURNS:
            self._display_image_kenburns(image_path, display_time)
        else:
            self._display_image_simple(image_path)

        if show_info:
            self._update_info_labels(image_data)

    def _display_image_simple(self, image_path):
        """Display image with no transition."""
        try:
            control = self.getControl(self.IMAGE_CONTROL_1)
            control.setImage(image_path, useCache=False)
            xbmc.log(f"[screensaver.immich] Set image on control {self.IMAGE_CONTROL_1}", xbmc.LOGINFO)
        except RuntimeError as e:
            xbmc.log(f"[screensaver.immich] Error setting image: {e}", xbmc.LOGERROR)

    def _display_image_crossfade(self, image_path):
        """Display image with crossfade transition."""
        try:
            # Get both controls
            control1 = self.getControl(self.IMAGE_CONTROL_1)
            control2 = self.getControl(self.IMAGE_CONTROL_2)

            # Determine which control to fade in
            if self.current_control == 1:
                # Fade in on control 2
                control2.setImage(image_path, useCache=False)

                # Animate: fade out control 1, fade in control 2
                for alpha in range(100, -1, -5):
                    if not self.is_active:
                        break
                    control1.setColorDiffuse('FF{:02X}{:02X}{:02X}'.format(
                        int(255 * alpha / 100), int(255 * alpha / 100), int(255 * alpha / 100)))
                    control2.setColorDiffuse('FF{:02X}{:02X}{:02X}'.format(
                        int(255 * (100 - alpha) / 100), int(255 * (100 - alpha) / 100), int(255 * (100 - alpha) / 100)))
                    xbmc.sleep(30)

                self.current_control = 2
            else:
                # Fade in on control 1
                control1.setImage(image_path, useCache=False)

                # Animate: fade out control 2, fade in control 1
                for alpha in range(100, -1, -5):
                    if not self.is_active:
                        break
                    control2.setColorDiffuse('FF{:02X}{:02X}{:02X}'.format(
                        int(255 * alpha / 100), int(255 * alpha / 100), int(255 * alpha / 100)))
                    control1.setColorDiffuse('FF{:02X}{:02X}{:02X}'.format(
                        int(255 * (100 - alpha) / 100), int(255 * (100 - alpha) / 100), int(255 * (100 - alpha) / 100)))
                    xbmc.sleep(30)

                self.current_control = 1

            xbmc.log(f"[screensaver.immich] Crossfade complete to control {self.current_control}", xbmc.LOGDEBUG)
        except RuntimeError as e:
            xbmc.log(f"[screensaver.immich] Error in crossfade: {e}", xbmc.LOGERROR)
            # Fallback to simple
            self._display_image_simple(image_path)

    def _display_image_kenburns(self, image_path, display_time):
        """Display image with Ken Burns (pan/zoom) effect."""
        try:
            control = self.getControl(self.IMAGE_CONTROL_1)
            control.setImage(image_path, useCache=False)

            # Random start and end positions for pan effect
            start_zoom = random.uniform(1.0, 1.1)
            end_zoom = random.uniform(1.0, 1.15)

            # Random pan direction
            start_x = random.randint(-50, 50)
            start_y = random.randint(-30, 30)
            end_x = random.randint(-50, 50)
            end_y = random.randint(-30, 30)

            # Note: Kodi's Python API doesn't support direct zoom/pan animation
            # The Ken Burns effect requires XML animations or a different approach
            # For now, just set the image and let CSS handle it if available
            xbmc.log(f"[screensaver.immich] Ken Burns display on control {self.IMAGE_CONTROL_1}", xbmc.LOGINFO)

        except RuntimeError as e:
            xbmc.log(f"[screensaver.immich] Error in Ken Burns: {e}", xbmc.LOGERROR)
            self._display_image_simple(image_path)

    def _update_info_labels(self, image_data):
        """Update info labels."""
        created_at = image_data.get('fileCreatedAt', '') or image_data.get('createdAt', '')
        exif = image_data.get('exifInfo', {}) or {}

        date_str = self._format_date(created_at)
        location_str = self._format_location(exif)
        desc_str = self._format_description(image_data, exif)

        try:
            self.getControl(self.DATE_LABEL).setLabel(date_str)
        except RuntimeError:
            pass

        try:
            self.getControl(self.LOCATION_LABEL).setLabel(location_str)
        except RuntimeError:
            pass

        try:
            self.getControl(self.DESCRIPTION_LABEL).setLabel(desc_str)
        except RuntimeError:
            pass

    def _format_date(self, date_string):
        if not date_string:
            return ''
        try:
            if 'T' in date_string:
                dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            else:
                dt = datetime.strptime(date_string[:10], '%Y-%m-%d')
            return dt.strftime('%A, %B %d, %Y')
        except (ValueError, TypeError):
            return date_string[:10] if len(date_string) >= 10 else date_string

    def _format_location(self, exif):
        city = exif.get('city', '')
        state = exif.get('state', '')
        country = exif.get('country', '')
        parts = [p for p in [city, state, country] if p]
        return ', '.join(parts) if parts else ''

    def _format_description(self, image_data, exif):
        desc = image_data.get('description', '')
        if desc:
            return desc
        make = exif.get('make', '')
        model = exif.get('model', '')
        if make and model:
            return model if make.lower() in model.lower() else f"{make} {model}"
        return model or make or ''

    def _show_error(self, message):
        xbmc.log(f"[screensaver.immich] Error: {message}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification(
            'Immich Screensaver',
            message,
            xbmcgui.NOTIFICATION_ERROR,
            5000
        )

    def _exit_callback(self):
        xbmc.log("[screensaver.immich] Exit callback triggered", xbmc.LOGINFO)
        self.is_active = False

    def onAction(self, action):
        xbmc.log(f"[screensaver.immich] Action received: {action.getId()}", xbmc.LOGDEBUG)
        self.is_active = False
        self.close()
