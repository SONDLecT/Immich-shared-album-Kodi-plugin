"""
Immich Slideshow - Interactive slideshow with pan/zoom effects
Based on the screensaver code, but with arrow key navigation.
"""

import os
import random
from datetime import datetime

import xbmc
import xbmcgui
import xbmcaddon


class ImmichSlideshow(xbmcgui.WindowXML):
    """Interactive slideshow with pan/zoom effects and arrow key navigation."""

    # Control IDs from XML
    IMAGE_CONTROL = 101
    INFO_OVERLAY = 300
    DATE_LABEL = 201
    LOCATION_LABEL = 202
    DESCRIPTION_LABEL = 203

    # Effect list matching official screensaver.picture.slideshow format
    EFFECTLIST = [
        # Zoom in from center
        [('conditional', 'effect=zoom start=100 end=%s center=auto time=%i condition=true')],
        # Zoom out from center
        [('conditional', 'effect=zoom start=%s end=100 center=auto time=%i condition=true')],
        # Pan left + zoom
        [('conditional', 'effect=slide start=0,0 end=-150,0 time=%i condition=true'),
         ('conditional', 'effect=zoom start=100 end=%s center=auto time=%i condition=true')],
        # Pan right + zoom
        [('conditional', 'effect=slide start=-150,0 end=0,0 time=%i condition=true'),
         ('conditional', 'effect=zoom start=100 end=%s center=auto time=%i condition=true')],
        # Pan up + zoom
        [('conditional', 'effect=slide start=0,0 end=0,-100 time=%i condition=true'),
         ('conditional', 'effect=zoom start=100 end=%s center=auto time=%i condition=true')],
        # Pan down + zoom
        [('conditional', 'effect=slide start=0,-100 end=0,0 time=%i condition=true'),
         ('conditional', 'effect=zoom start=100 end=%s center=auto time=%i condition=true')],
    ]

    # Kodi action IDs
    ACTION_PREVIOUS_MENU = 10
    ACTION_NAV_BACK = 92
    ACTION_STOP = 13
    ACTION_MOVE_LEFT = 1
    ACTION_MOVE_RIGHT = 2
    ACTION_MOVE_UP = 3
    ACTION_MOVE_DOWN = 4
    ACTION_SELECT_ITEM = 7
    ACTION_PAUSE = 12

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.addon = xbmcaddon.Addon()
        self.client = kwargs.get('client')
        self.assets = kwargs.get('assets', [])
        self.current_index = kwargs.get('start_index', 0)
        self.is_active = True
        self.is_paused = False
        self.auto_advance = True
        self.display_time = 10
        self.ken_burns = True
        self.show_info = True

    def onInit(self):
        """Called when the slideshow window is initialized."""
        xbmc.log("[plugin.image.immich] Slideshow starting", xbmc.LOGINFO)

        if not self.assets:
            xbmc.log("[plugin.image.immich] No assets for slideshow", xbmc.LOGERROR)
            self.close()
            return

        # Get display settings from addon
        try:
            self.display_time = int(self.addon.getSetting('slideshow_interval') or '10')
        except ValueError:
            self.display_time = 10

        self.ken_burns = self.addon.getSetting('slideshow_effect') == 'true'
        self.show_info = self.addon.getSetting('slideshow_info') == 'true'

        # Configure info overlay visibility
        self._set_info_visibility(self.show_info)

        # Main display loop
        xbmc.log(f"[plugin.image.immich] Slideshow with {len(self.assets)} images", xbmc.LOGINFO)

        while self.is_active:
            if self.current_index < 0:
                self.current_index = len(self.assets) - 1
            elif self.current_index >= len(self.assets):
                self.current_index = 0

            asset = self.assets[self.current_index]
            self._display_asset(asset)

            # Wait for display time or user input (check every 100ms)
            waited = 0
            while waited < self.display_time and self.is_active and self.auto_advance and not self.is_paused:
                xbmc.sleep(100)
                waited += 0.1

            # Auto-advance to next image if not paused
            if self.auto_advance and not self.is_paused and self.is_active:
                self.current_index += 1

        self.close()

    def _display_asset(self, asset):
        """Display an asset with optional pan/zoom effect."""
        try:
            asset_id = asset.get('id')
            if not asset_id:
                return

            # Get image path
            image_path = self.client.get_asset_original(asset_id)
            if not image_path or not os.path.exists(image_path):
                xbmc.log(f"[plugin.image.immich] Invalid path: {image_path}", xbmc.LOGWARNING)
                return

            # Update info labels first
            if self.show_info:
                self._update_info_labels(asset)

            control = self.getControl(self.IMAGE_CONTROL)

            if self.ken_burns:
                # Calculate animation time
                anim_time = self.display_time * 1000
                zoom = min(110 + (self.display_time * 2), 150)

                # Pick a random effect
                effect_template = random.choice(self.EFFECTLIST)

                # Build animation list
                animations = []
                for anim_type, effect_str in effect_template:
                    if '%s' in effect_str and '%i' in effect_str:
                        formatted = effect_str % (zoom, anim_time)
                    elif '%i' in effect_str:
                        formatted = effect_str % anim_time
                    else:
                        formatted = effect_str
                    animations.append((anim_type, formatted))

                control.setAnimations(animations)

            # Set the image
            control.setImage(image_path, useCache=False)

        except RuntimeError as e:
            xbmc.log(f"[plugin.image.immich] Display error: {e}", xbmc.LOGERROR)

    def _set_info_visibility(self, visible):
        """Set visibility of info overlay and labels."""
        try:
            self.getControl(self.INFO_OVERLAY).setVisible(visible)
        except RuntimeError:
            pass

        for label_id in [self.DATE_LABEL, self.LOCATION_LABEL, self.DESCRIPTION_LABEL]:
            try:
                self.getControl(label_id).setVisible(visible)
            except RuntimeError:
                pass

    def _update_info_labels(self, asset):
        """Update info labels with asset metadata."""
        created_at = asset.get('fileCreatedAt', '') or asset.get('createdAt', '')
        exif = asset.get('exifInfo', {}) or {}

        # Show position in slideshow
        position = f"[{self.current_index + 1}/{len(self.assets)}] "

        try:
            date_str = self._format_date(created_at)
            self.getControl(self.DATE_LABEL).setLabel(position + date_str)
        except RuntimeError:
            pass

        try:
            self.getControl(self.LOCATION_LABEL).setLabel(self._format_location(exif))
        except RuntimeError:
            pass

        try:
            self.getControl(self.DESCRIPTION_LABEL).setLabel(self._format_description(asset, exif))
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

    def _format_description(self, asset, exif):
        desc = asset.get('description', '')
        if desc:
            return desc
        make = exif.get('make', '')
        model = exif.get('model', '')
        if make and model:
            return model if make.lower() in model.lower() else f"{make} {model}"
        return model or make or ''

    def onAction(self, action):
        """Handle user input for navigation."""
        action_id = action.getId()

        if action_id in (self.ACTION_PREVIOUS_MENU, self.ACTION_NAV_BACK, self.ACTION_STOP):
            # Exit slideshow
            self.is_active = False
            self.close()

        elif action_id == self.ACTION_MOVE_LEFT:
            # Previous image
            self.auto_advance = False
            self.current_index -= 1
            if self.current_index < 0:
                self.current_index = len(self.assets) - 1
            self._display_asset(self.assets[self.current_index])

        elif action_id == self.ACTION_MOVE_RIGHT:
            # Next image
            self.auto_advance = False
            self.current_index += 1
            if self.current_index >= len(self.assets):
                self.current_index = 0
            self._display_asset(self.assets[self.current_index])

        elif action_id in (self.ACTION_SELECT_ITEM, self.ACTION_PAUSE):
            # Toggle pause/play
            self.is_paused = not self.is_paused
            if not self.is_paused:
                self.auto_advance = True
            status = "Paused" if self.is_paused else "Playing"
            xbmc.executebuiltin(f'Notification(Slideshow, {status}, 1000)')

        elif action_id == self.ACTION_MOVE_UP:
            # Toggle info overlay
            self.show_info = not self.show_info
            self._set_info_visibility(self.show_info)

        elif action_id == self.ACTION_MOVE_DOWN:
            # Toggle pan/zoom effect
            self.ken_burns = not self.ken_burns
            effect_status = "Pan/Zoom On" if self.ken_burns else "Pan/Zoom Off"
            xbmc.executebuiltin(f'Notification(Slideshow, {effect_status}, 1000)')


def start_slideshow(client, assets, start_index=0):
    """
    Start the slideshow with the given assets.

    Args:
        client: ImmichClient instance for fetching images
        assets: List of asset dictionaries
        start_index: Index of the first image to display
    """
    if not assets:
        xbmcgui.Dialog().notification(
            'Immich',
            'No images to display',
            xbmcgui.NOTIFICATION_INFO
        )
        return

    # Filter to only images
    image_assets = [a for a in assets if a.get('type') == 'IMAGE']

    if not image_assets:
        xbmcgui.Dialog().notification(
            'Immich',
            'No images found',
            xbmcgui.NOTIFICATION_INFO
        )
        return

    addon = xbmcaddon.Addon()
    addon_path = addon.getAddonInfo('path')

    # Create the slideshow window
    slideshow = ImmichSlideshow(
        'slideshow-immich.xml',
        addon_path,
        'default',
        '1080i',
        client=client,
        assets=image_assets,
        start_index=start_index
    )

    slideshow.doModal()
    del slideshow
