"""
Immich API Client
Handles all communication with the Immich server
"""

import os
import hashlib
import requests
import xbmc
import xbmcvfs
import xbmcaddon


class ImmichClient:
    """Client for interacting with the Immich API."""

    def __init__(self, server_url, api_key):
        """
        Initialize the Immich client.

        Args:
            server_url: Base URL of the Immich server (e.g., https://immich.example.com)
            api_key: API key for authentication
        """
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.base_url = f"{self.server_url}/api"
        self.headers = {
            'x-api-key': api_key,
            'Accept': 'application/json'
        }
        # Set up cache directory
        addon = xbmcaddon.Addon()
        self.cache_dir = os.path.join(
            xbmcvfs.translatePath(addon.getAddonInfo('profile')),
            'cache'
        )
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def _request(self, method, endpoint, params=None, json_data=None):
        """
        Make an authenticated request to the Immich API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            params: Query parameters
            json_data: JSON body data

        Returns:
            Response JSON or None on error
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            response = requests.request(
                method,
                url,
                headers=self.headers,
                params=params,
                json=json_data,
                timeout=30
            )
            response.raise_for_status()
            return response.json() if response.content else None
        except requests.exceptions.RequestException as e:
            xbmc.log(f"[plugin.image.immich] API request failed: {e}", xbmc.LOGERROR)
            return None

    def _download_to_cache(self, url, cache_key, extension='.jpg'):
        """
        Download a file to local cache with authentication headers.

        Args:
            url: URL to download
            cache_key: Unique key for caching
            extension: File extension

        Returns:
            Local file path or None on error
        """
        # Create cache filename from hash of key
        filename = hashlib.md5(cache_key.encode()).hexdigest() + extension
        cache_path = os.path.join(self.cache_dir, filename)

        # Return cached file if it exists
        if os.path.exists(cache_path):
            return cache_path

        try:
            response = requests.get(url, headers=self.headers, timeout=30, stream=True)
            response.raise_for_status()

            with open(cache_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return cache_path
        except requests.exceptions.RequestException as e:
            xbmc.log(f"[plugin.image.immich] Download failed: {e}", xbmc.LOGERROR)
            return None

    def test_connection(self):
        """
        Test the connection to the Immich server.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/server/ping",
                headers=self.headers,
                timeout=10
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def get_my_user(self):
        """Get the current authenticated user's information."""
        return self._request('GET', '/users/me')

    # Album methods
    def get_all_albums(self, shared=None):
        """
        Get all albums.

        Args:
            shared: If True, only shared albums. If False, only owned albums. If None, all.

        Returns:
            List of album objects
        """
        params = {}
        if shared is not None:
            params['shared'] = str(shared).lower()
        return self._request('GET', '/albums', params=params) or []

    def get_album(self, album_id):
        """
        Get a specific album with its assets.

        Args:
            album_id: The album's unique identifier

        Returns:
            Album object with assets
        """
        return self._request('GET', f'/albums/{album_id}')

    # Shared links methods
    def get_shared_links(self):
        """
        Get all shared links created by the user.

        Returns:
            List of shared link objects
        """
        return self._request('GET', '/shared-links') or []

    def get_shared_link_by_key(self, key, password=None):
        """
        Access a shared link by its key.

        Args:
            key: The shared link key
            password: Optional password if the link is password-protected

        Returns:
            Shared link object with assets
        """
        headers = self.headers.copy()
        if password:
            headers['password'] = password
        try:
            response = requests.get(
                f"{self.base_url}/shared-links/me",
                headers=headers,
                params={'key': key},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            xbmc.log(f"[plugin.image.immich] Failed to get shared link: {e}", xbmc.LOGERROR)
            return None

    # Asset methods
    def get_asset_info(self, asset_id):
        """
        Get information about a specific asset.

        Args:
            asset_id: The asset's unique identifier

        Returns:
            Asset object
        """
        return self._request('GET', f'/assets/{asset_id}')

    def get_asset_thumbnail(self, asset_id, size='preview'):
        """
        Download and cache an asset's thumbnail.

        Args:
            asset_id: The asset's unique identifier
            size: Thumbnail size ('thumbnail' or 'preview')

        Returns:
            Local file path to the cached thumbnail
        """
        url = f"{self.base_url}/assets/{asset_id}/thumbnail?size={size}"
        cache_key = f"thumb_{asset_id}_{size}"
        return self._download_to_cache(url, cache_key, '.jpg')

    def get_asset_original(self, asset_id):
        """
        Download and cache an asset's original file.

        Args:
            asset_id: The asset's unique identifier

        Returns:
            Local file path to the cached original
        """
        # Get asset info to determine file type
        asset_info = self.get_asset_info(asset_id)
        ext = '.jpg'
        if asset_info:
            filename = asset_info.get('originalFileName', '')
            if '.' in filename:
                ext = '.' + filename.rsplit('.', 1)[-1].lower()

        url = f"{self.base_url}/assets/{asset_id}/original"
        cache_key = f"orig_{asset_id}"
        return self._download_to_cache(url, cache_key, ext)

    def get_asset_video_playback(self, asset_id):
        """
        Download and cache a video for playback.

        Args:
            asset_id: The asset's unique identifier

        Returns:
            Local file path to the cached video
        """
        url = f"{self.base_url}/assets/{asset_id}/video/playback"
        cache_key = f"video_{asset_id}"
        return self._download_to_cache(url, cache_key, '.mp4')

    # Favorites
    def get_favorites(self, count=100):
        """
        Get favorite assets using smart search.

        Args:
            count: Maximum number of favorites to return

        Returns:
            List of favorite asset objects
        """
        result = self._request('POST', '/search/smart', json_data={
            'isFavorite': True,
            'size': count
        })
        if result and 'assets' in result:
            return result['assets'].get('items', [])
        return []

    # Timeline/All assets
    def get_timeline_buckets(self):
        """
        Get timeline buckets (grouped by time period).

        Returns:
            List of timeline bucket objects
        """
        return self._request('GET', '/timeline/buckets') or []

    def get_timeline_bucket(self, time_bucket):
        """
        Get assets for a specific timeline bucket.

        Args:
            time_bucket: The time bucket identifier

        Returns:
            List of assets in the bucket
        """
        return self._request('GET', '/timeline/bucket', params={
            'timeBucket': time_bucket
        }) or []

    # Search
    def search_assets(self, query, media_type=None):
        """
        Search for assets using smart search.

        Args:
            query: Search query string
            media_type: Optional filter ('IMAGE' or 'VIDEO')

        Returns:
            Search results object
        """
        search_params = {'query': query}
        if media_type:
            search_params['type'] = media_type
        return self._request('POST', '/search/smart', json_data=search_params)

    def search_metadata(self, query):
        """
        Search assets by metadata.

        Args:
            query: Search query string

        Returns:
            Search results
        """
        return self._request('POST', '/search/metadata', json_data={
            'originalFileName': query
        })

    # People (face recognition)
    def get_all_people(self, with_hidden=False):
        """
        Get all recognized people.

        Args:
            with_hidden: Include hidden people

        Returns:
            List of person objects
        """
        result = self._request('GET', '/people', params={
            'withHidden': str(with_hidden).lower(),
            'size': 500
        })
        if result and 'people' in result:
            return result['people']
        return result if isinstance(result, list) else []

    def get_person(self, person_id):
        """
        Get a specific person's details.

        Args:
            person_id: The person's unique identifier

        Returns:
            Person object
        """
        return self._request('GET', f'/people/{person_id}')

    def get_person_thumbnail(self, person_id):
        """
        Download and cache a person's face thumbnail.

        Args:
            person_id: The person's unique identifier

        Returns:
            Local file path to the cached thumbnail
        """
        url = f"{self.base_url}/people/{person_id}/thumbnail"
        cache_key = f"person_{person_id}"
        return self._download_to_cache(url, cache_key, '.jpg')

    def get_person_assets(self, person_id, count=200):
        """
        Get all assets featuring a specific person.

        Args:
            person_id: The person's unique identifier
            count: Maximum number of assets to return

        Returns:
            List of asset objects
        """
        result = self._request('POST', '/search/smart', json_data={
            'personIds': [person_id],
            'size': count
        })
        if result and 'assets' in result:
            return result['assets'].get('items', [])
        return []

    # Server info
    def get_server_info(self):
        """Get server version and feature information."""
        return self._request('GET', '/server/info')

    def get_server_statistics(self):
        """Get server statistics (admin only)."""
        return self._request('GET', '/server/statistics')
