"""
Immich Kodi Plugin - UI and Navigation Logic
"""

import urllib.parse

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon


class ImmichPlugin:
    """Handles Kodi UI and navigation for the Immich plugin."""

    def __init__(self, handle, base_url, addon, client):
        """
        Initialize the plugin.

        Args:
            handle: Kodi plugin handle
            base_url: Plugin base URL
            addon: Kodi addon instance
            client: ImmichClient instance
        """
        self.handle = handle
        self.base_url = base_url
        self.addon = addon
        self.client = client
        self.addon_id = addon.getAddonInfo('id')
        self._heif_warned = False

    def _check_heif_addon(self):
        """Check if HEIF image decoder is installed and warn if not."""
        if self._heif_warned:
            return
        try:
            xbmcaddon.Addon('imagedecoder.heif')
        except RuntimeError:
            # HEIF addon not installed - show one-time warning
            self._heif_warned = True
            xbmcgui.Dialog().notification(
                'HEIF Decoder Missing',
                'Install "HEIF image decoder" addon for Apple HEIC photo support',
                xbmcgui.NOTIFICATION_WARNING,
                5000
            )

    def _build_url(self, **kwargs):
        """Build a plugin URL with the given parameters."""
        return f"{self.base_url}?{urllib.parse.urlencode(kwargs)}"

    def _add_directory_item(self, label, url, is_folder=True, thumb=None, fanart=None,
                            info_labels=None, context_menu=None):
        """Add a directory item to the listing."""
        list_item = xbmcgui.ListItem(label=label)

        if thumb:
            list_item.setArt({'thumb': thumb, 'icon': thumb})
        if fanart:
            list_item.setArt({'fanart': fanart})

        if info_labels:
            list_item.setInfo('pictures', info_labels)

        if context_menu:
            list_item.addContextMenuItems(context_menu)

        xbmcplugin.addDirectoryItem(
            handle=self.handle,
            url=url,
            listitem=list_item,
            isFolder=is_folder
        )

    def _add_image_item(self, asset, album_id=None):
        """Add an image asset to the listing."""
        asset_id = asset.get('id')
        asset_type = asset.get('type', 'IMAGE')
        filename = asset.get('originalFileName', 'Unknown')
        created_at = asset.get('fileCreatedAt', '')

        # Don't download thumbnails for listing - use default icon
        # Thumbnails will be downloaded on-demand when viewing
        list_item = xbmcgui.ListItem(label=filename)
        list_item.setArt({
            'thumb': self.addon.getAddonInfo('icon'),
            'icon': self.addon.getAddonInfo('icon')
        })

        # Set properties for images
        info = {'title': filename}
        if created_at:
            info['date'] = created_at[:10] if len(created_at) >= 10 else created_at

        list_item.setInfo('pictures', info)

        # Set video info if it's a video
        if asset_type == 'VIDEO':
            list_item.setInfo('video', {'title': filename})
            list_item.setProperty('IsPlayable', 'true')
            url = self._build_url(action='play_video', asset_id=asset_id)
            is_folder = False
        else:
            # For images, use original file (requires HEIF addon for Apple photos)
            url = self.client.get_asset_original(asset_id)
            is_folder = False
            list_item.setProperty('IsPlayable', 'false')

        # Add context menu for slideshow
        context_menu = []
        if album_id:
            context_menu.append((
                'Start Slideshow from Here',
                f'RunPlugin({self._build_url(action="slideshow", album_id=album_id)})'
            ))

        if context_menu:
            list_item.addContextMenuItems(context_menu)

        xbmcplugin.addDirectoryItem(
            handle=self.handle,
            url=url,
            listitem=list_item,
            isFolder=is_folder
        )

    def _end_directory(self, content_type='images', sort_methods=None, update_listing=False):
        """Finalize the directory listing."""
        if content_type:
            xbmcplugin.setContent(self.handle, content_type)

        if sort_methods:
            for method in sort_methods:
                xbmcplugin.addSortMethod(self.handle, method)
        else:
            xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_NONE)

        xbmcplugin.endOfDirectory(self.handle, updateListing=update_listing)

    def show_main_menu(self):
        """Display the main menu."""
        # Test connection first
        if not self.client.test_connection():
            xbmcgui.Dialog().ok(
                self.addon.getAddonInfo('name'),
                'Cannot connect to Immich server. Please check your settings.'
            )
            return

        # My Albums
        self._add_directory_item(
            label='My Albums',
            url=self._build_url(action='albums'),
            thumb=self.addon.getAddonInfo('icon')
        )

        # Shared Albums
        self._add_directory_item(
            label='Shared Albums',
            url=self._build_url(action='shared_albums'),
            thumb=self.addon.getAddonInfo('icon')
        )

        # Shared Links
        self._add_directory_item(
            label='Shared Links',
            url=self._build_url(action='shared_links'),
            thumb=self.addon.getAddonInfo('icon')
        )

        # Favorites
        self._add_directory_item(
            label='Favorites',
            url=self._build_url(action='favorites'),
            thumb=self.addon.getAddonInfo('icon')
        )

        # People
        self._add_directory_item(
            label='People',
            url=self._build_url(action='people'),
            thumb=self.addon.getAddonInfo('icon')
        )

        # Timeline
        self._add_directory_item(
            label='Timeline',
            url=self._build_url(action='timeline'),
            thumb=self.addon.getAddonInfo('icon')
        )

        # Search
        self._add_directory_item(
            label='Search',
            url=self._build_url(action='search'),
            thumb=self.addon.getAddonInfo('icon')
        )

        self._end_directory(content_type='files')

    def show_albums(self):
        """Display user's own albums."""
        albums = self.client.get_all_albums(shared=False)

        if not albums:
            xbmcgui.Dialog().notification(
                self.addon.getAddonInfo('name'),
                'No albums found',
                xbmcgui.NOTIFICATION_INFO
            )
            self._end_directory()
            return

        for album in albums:
            album_id = album.get('id')
            album_name = album.get('albumName', 'Unnamed Album')
            asset_count = album.get('assetCount', 0)

            # Get thumbnail from album cover or first asset
            thumb = None
            if album.get('albumThumbnailAssetId'):
                thumb = self.client.get_asset_thumbnail(
                    album.get('albumThumbnailAssetId'),
                    'preview'
                )

            self._add_directory_item(
                label=f"{album_name} ({asset_count})",
                url=self._build_url(action='album', album_id=album_id),
                thumb=thumb,
                info_labels={'title': album_name}
            )

        self._end_directory(
            content_type='images',
            sort_methods=[xbmcplugin.SORT_METHOD_LABEL]
        )

    def show_shared_albums(self):
        """Display shared albums."""
        albums = self.client.get_all_albums(shared=True)

        if not albums:
            xbmcgui.Dialog().notification(
                self.addon.getAddonInfo('name'),
                'No shared albums found',
                xbmcgui.NOTIFICATION_INFO
            )
            self._end_directory()
            return

        for album in albums:
            album_id = album.get('id')
            album_name = album.get('albumName', 'Unnamed Album')
            asset_count = album.get('assetCount', 0)
            owner = album.get('owner', {})
            owner_name = owner.get('name', 'Unknown')

            # Get thumbnail
            thumb = None
            if album.get('albumThumbnailAssetId'):
                thumb = self.client.get_asset_thumbnail(
                    album.get('albumThumbnailAssetId'),
                    'preview'
                )

            self._add_directory_item(
                label=f"{album_name} ({asset_count}) - by {owner_name}",
                url=self._build_url(action='album', album_id=album_id),
                thumb=thumb,
                info_labels={'title': album_name}
            )

        self._end_directory(
            content_type='images',
            sort_methods=[xbmcplugin.SORT_METHOD_LABEL]
        )

    def show_shared_links(self):
        """Display shared links created by the user."""
        links = self.client.get_shared_links()

        if not links:
            xbmcgui.Dialog().notification(
                self.addon.getAddonInfo('name'),
                'No shared links found',
                xbmcgui.NOTIFICATION_INFO
            )
            self._end_directory()
            return

        for link in links:
            link_key = link.get('key')
            description = link.get('description', 'Shared Link')
            album = link.get('album')
            asset_count = len(link.get('assets', []))

            if album:
                label = f"Album: {album.get('albumName', 'Unknown')} ({asset_count})"
            else:
                label = f"{description} ({asset_count} assets)"

            self._add_directory_item(
                label=label,
                url=self._build_url(action='shared_link', link_key=link_key),
                info_labels={'title': description}
            )

        self._end_directory(content_type='images')

    def show_album_contents(self, album_id):
        """Display contents of an album."""
        if not album_id:
            xbmcgui.Dialog().notification(
                self.addon.getAddonInfo('name'),
                'Invalid album ID',
                xbmcgui.NOTIFICATION_ERROR
            )
            return

        album = self.client.get_album(album_id)

        if not album:
            xbmcgui.Dialog().notification(
                self.addon.getAddonInfo('name'),
                'Could not load album',
                xbmcgui.NOTIFICATION_ERROR
            )
            return

        assets = album.get('assets', [])

        if not assets:
            xbmcgui.Dialog().notification(
                self.addon.getAddonInfo('name'),
                'Album is empty',
                xbmcgui.NOTIFICATION_INFO
            )
            self._end_directory()
            return

        # Add slideshow option at the top
        self._add_directory_item(
            label='[Start Slideshow]',
            url=self._build_url(action='slideshow', album_id=album_id),
            is_folder=False,
            thumb=self.addon.getAddonInfo('icon')
        )

        for asset in assets:
            self._add_image_item(asset, album_id=album_id)

        self._end_directory(
            content_type='images',
            sort_methods=[
                xbmcplugin.SORT_METHOD_NONE,
                xbmcplugin.SORT_METHOD_LABEL,
                xbmcplugin.SORT_METHOD_DATE
            ]
        )

    def show_shared_link_contents(self, link_key):
        """Display contents of a shared link."""
        if not link_key:
            xbmcgui.Dialog().notification(
                self.addon.getAddonInfo('name'),
                'Invalid shared link',
                xbmcgui.NOTIFICATION_ERROR
            )
            return

        link_data = self.client.get_shared_link_by_key(link_key)

        if not link_data:
            xbmcgui.Dialog().notification(
                self.addon.getAddonInfo('name'),
                'Could not load shared link',
                xbmcgui.NOTIFICATION_ERROR
            )
            return

        assets = link_data.get('assets', [])

        if not assets:
            xbmcgui.Dialog().notification(
                self.addon.getAddonInfo('name'),
                'Shared link has no assets',
                xbmcgui.NOTIFICATION_INFO
            )
            self._end_directory()
            return

        for asset in assets:
            self._add_image_item(asset)

        self._end_directory(content_type='images')

    def show_favorites(self):
        """Display favorite assets."""
        assets = self.client.get_favorites()

        if not assets:
            xbmcgui.Dialog().notification(
                self.addon.getAddonInfo('name'),
                'No favorites found',
                xbmcgui.NOTIFICATION_INFO
            )
            self._end_directory()
            return

        for asset in assets:
            self._add_image_item(asset)

        self._end_directory(content_type='images')

    def show_people(self):
        """Display all recognized people."""
        people = self.client.get_all_people()

        if not people:
            xbmcgui.Dialog().notification(
                self.addon.getAddonInfo('name'),
                'No people found',
                xbmcgui.NOTIFICATION_INFO
            )
            self._end_directory()
            return

        for person in people:
            person_id = person.get('id')
            name = person.get('name', '')
            birth_date = person.get('birthDate', '')

            # Use name if set, otherwise show as "Unknown"
            if name:
                label = name
            else:
                label = 'Unknown Person'

            # Add birth date if available
            if birth_date:
                label = f"{label} ({birth_date[:4]})"

            # Get face thumbnail
            thumb = self.client.get_person_thumbnail(person_id)

            # Context menu to start slideshow
            context_menu = [(
                'Start Slideshow',
                f'RunPlugin({self._build_url(action="person_slideshow", person_id=person_id)})'
            )]

            self._add_directory_item(
                label=label,
                url=self._build_url(action='person', person_id=person_id),
                thumb=thumb,
                info_labels={'title': name or 'Unknown'},
                context_menu=context_menu
            )

        self._end_directory(
            content_type='images',
            sort_methods=[xbmcplugin.SORT_METHOD_LABEL]
        )

    def show_person_photos(self, person_id):
        """Display all photos of a specific person."""
        if not person_id:
            xbmcgui.Dialog().notification(
                self.addon.getAddonInfo('name'),
                'Invalid person',
                xbmcgui.NOTIFICATION_ERROR
            )
            return

        # Get person info for the title
        person = self.client.get_person(person_id)
        person_name = person.get('name', 'Unknown') if person else 'Unknown'

        assets = self.client.get_person_assets(person_id)

        if not assets:
            xbmcgui.Dialog().notification(
                self.addon.getAddonInfo('name'),
                f'No photos found for {person_name}',
                xbmcgui.NOTIFICATION_INFO
            )
            self._end_directory()
            return

        # Add slideshow option at the top
        self._add_directory_item(
            label=f'[Start Slideshow - {person_name}]',
            url=self._build_url(action='person_slideshow', person_id=person_id),
            is_folder=False,
            thumb=self.client.get_person_thumbnail(person_id)
        )

        for asset in assets:
            self._add_image_item(asset)

        self._end_directory(
            content_type='images',
            sort_methods=[
                xbmcplugin.SORT_METHOD_NONE,
                xbmcplugin.SORT_METHOD_DATE
            ]
        )

    def start_person_slideshow(self, person_id):
        """Start a slideshow for a person's photos."""
        if not person_id:
            return

        assets = self.client.get_person_assets(person_id)
        image_assets = [a for a in assets if a.get('type') == 'IMAGE']

        if not image_assets:
            xbmcgui.Dialog().notification(
                self.addon.getAddonInfo('name'),
                'No images found for this person',
                xbmcgui.NOTIFICATION_INFO
            )
            return

        # Download and show the first image (requires HEIF addon for Apple photos)
        self._check_heif_addon()
        first_image_path = self.client.get_asset_original(image_assets[0].get('id'))
        if first_image_path:
            xbmc.executebuiltin(f'ShowPicture({first_image_path})')

    def show_timeline(self):
        """Display timeline buckets."""
        buckets = self.client.get_timeline_buckets()

        if not buckets:
            xbmcgui.Dialog().notification(
                self.addon.getAddonInfo('name'),
                'No timeline data found',
                xbmcgui.NOTIFICATION_INFO
            )
            self._end_directory()
            return

        for bucket in buckets:
            time_bucket = bucket.get('timeBucket', '')
            count = bucket.get('count', 0)

            # Format the time bucket for display (YYYY-MM format)
            if len(time_bucket) >= 7:
                display_date = time_bucket[:7]  # YYYY-MM
            else:
                display_date = time_bucket

            self._add_directory_item(
                label=f"{display_date} ({count})",
                url=self._build_url(action='timeline_bucket', bucket=time_bucket),
                info_labels={'title': display_date}
            )

        self._end_directory(content_type='images')

    def show_timeline_bucket(self, time_bucket):
        """Display assets from a specific timeline bucket."""
        if not time_bucket:
            xbmcgui.Dialog().notification(
                self.addon.getAddonInfo('name'),
                'Invalid time bucket',
                xbmcgui.NOTIFICATION_ERROR
            )
            return

        assets = self.client.get_timeline_bucket(time_bucket)

        if not assets:
            xbmcgui.Dialog().notification(
                self.addon.getAddonInfo('name'),
                'No photos in this period',
                xbmcgui.NOTIFICATION_INFO
            )
            self._end_directory()
            return

        for asset in assets:
            self._add_image_item(asset)

        self._end_directory(
            content_type='images',
            sort_methods=[
                xbmcplugin.SORT_METHOD_NONE,
                xbmcplugin.SORT_METHOD_DATE
            ]
        )

    def view_image(self, asset_id):
        """View a single image."""
        if not asset_id:
            return

        self._check_heif_addon()
        image_path = self.client.get_asset_original(asset_id)
        if image_path:
            xbmc.executebuiltin(f'ShowPicture({image_path})')

    def play_video(self, asset_id):
        """Play a video asset."""
        if not asset_id:
            return

        video_url = self.client.get_asset_video_playback(asset_id)
        asset_info = self.client.get_asset_info(asset_id)

        list_item = xbmcgui.ListItem(path=video_url)

        if asset_info:
            list_item.setInfo('video', {
                'title': asset_info.get('originalFileName', 'Video'),
                'mediatype': 'video'
            })

        xbmcplugin.setResolvedUrl(self.handle, True, list_item)

    def start_slideshow(self, album_id):
        """Start a slideshow for an album."""
        if not album_id:
            xbmcgui.Dialog().notification(
                self.addon.getAddonInfo('name'),
                'Invalid album',
                xbmcgui.NOTIFICATION_ERROR
            )
            return

        album = self.client.get_album(album_id)

        if not album or not album.get('assets'):
            xbmcgui.Dialog().notification(
                self.addon.getAddonInfo('name'),
                'Album has no images',
                xbmcgui.NOTIFICATION_INFO
            )
            return

        # Get image URLs for the slideshow
        assets = album.get('assets', [])
        image_assets = [a for a in assets if a.get('type') == 'IMAGE']

        if not image_assets:
            xbmcgui.Dialog().notification(
                self.addon.getAddonInfo('name'),
                'No images in album',
                xbmcgui.NOTIFICATION_INFO
            )
            return

        # Download and show the first image (requires HEIF addon for Apple photos)
        # User can navigate with arrow keys in Kodi's picture viewer
        self._check_heif_addon()
        first_image_path = self.client.get_asset_original(image_assets[0].get('id'))
        if first_image_path:
            xbmc.executebuiltin(f'ShowPicture({first_image_path})')

    def search(self):
        """Show search dialog and display results."""
        keyboard = xbmc.Keyboard('', 'Search Immich')
        keyboard.doModal()

        if not keyboard.isConfirmed():
            return

        query = keyboard.getText()
        if not query:
            return

        # Perform search
        results = self.client.search_assets(query)

        if not results:
            xbmcgui.Dialog().notification(
                self.addon.getAddonInfo('name'),
                'No results found',
                xbmcgui.NOTIFICATION_INFO
            )
            self._end_directory()
            return

        # Get assets from search results
        assets = results.get('assets', {}).get('items', [])

        if not assets:
            xbmcgui.Dialog().notification(
                self.addon.getAddonInfo('name'),
                'No results found',
                xbmcgui.NOTIFICATION_INFO
            )
            self._end_directory()
            return

        for asset in assets:
            self._add_image_item(asset)

        self._end_directory(content_type='images')
