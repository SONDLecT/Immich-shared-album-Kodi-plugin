"""
Immich API Client
Handles all communication with the Immich server
"""

import requests
import xbmc


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

    def get_asset_thumbnail_url(self, asset_id, size='preview'):
        """
        Get the URL for an asset's thumbnail.

        Args:
            asset_id: The asset's unique identifier
            size: Thumbnail size ('thumbnail' or 'preview')

        Returns:
            URL string for the thumbnail
        """
        return f"{self.base_url}/assets/{asset_id}/thumbnail?size={size}&api_key={self.api_key}"

    def get_asset_original_url(self, asset_id):
        """
        Get the URL for an asset's original file.

        Args:
            asset_id: The asset's unique identifier

        Returns:
            URL string for the original file
        """
        return f"{self.base_url}/assets/{asset_id}/original?api_key={self.api_key}"

    def get_asset_video_playback_url(self, asset_id):
        """
        Get the URL for video playback.

        Args:
            asset_id: The asset's unique identifier

        Returns:
            URL string for video playback
        """
        return f"{self.base_url}/assets/{asset_id}/video/playback?api_key={self.api_key}"

    # Favorites
    def get_favorites(self):
        """
        Get all favorite assets.

        Returns:
            List of favorite asset objects
        """
        return self._request('GET', '/assets', params={'isFavorite': 'true'}) or []

    # Timeline/All assets
    def get_timeline_buckets(self):
        """
        Get timeline buckets (grouped by time period).

        Returns:
            List of timeline bucket objects
        """
        return self._request('GET', '/timeline/buckets', params={'size': 'MONTH'}) or []

    def get_timeline_bucket(self, time_bucket):
        """
        Get assets for a specific timeline bucket.

        Args:
            time_bucket: The time bucket identifier

        Returns:
            List of assets in the bucket
        """
        return self._request('GET', '/timeline/bucket', params={
            'size': 'MONTH',
            'timeBucket': time_bucket
        }) or []

    # Search
    def search_assets(self, query, media_type=None):
        """
        Search for assets.

        Args:
            query: Search query string
            media_type: Optional filter ('IMAGE' or 'VIDEO')

        Returns:
            Search results object
        """
        search_params = {'q': query}
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

    # Server info
    def get_server_info(self):
        """Get server version and feature information."""
        return self._request('GET', '/server/info')

    def get_server_statistics(self):
        """Get server statistics (admin only)."""
        return self._request('GET', '/server/statistics')
