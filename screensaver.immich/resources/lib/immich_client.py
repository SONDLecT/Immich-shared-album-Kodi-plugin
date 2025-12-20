"""
Immich API Client for Screensaver
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
            xbmc.log(f"[screensaver.immich] API request failed: {e}", xbmc.LOGERROR)
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
            xbmc.log(f"[screensaver.immich] Download failed: {e}", xbmc.LOGERROR)
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

    def get_asset_info(self, asset_id):
        """
        Get information about a specific asset.

        Args:
            asset_id: The asset's unique identifier

        Returns:
            Asset object
        """
        return self._request('GET', f'/assets/{asset_id}')

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

    def search_random(self, count=100):
        """
        Get random assets from the library.

        Args:
            count: Number of assets to return

        Returns:
            List of random asset objects
        """
        result = self._request('POST', '/search/random', json_data={
            'count': count
        })
        return result if isinstance(result, list) else []

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
