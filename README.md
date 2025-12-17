# Immich Kodi Plugin

A Kodi addon to browse and view your [Immich](https://immich.app/) photo library directly in Kodi.

## Features

- **Browse Albums** - View your personal albums
- **Shared Albums** - Access albums shared with you by other users
- **Shared Links** - Browse shared links you've created
- **Favorites** - Quick access to your favorite photos and videos
- **Timeline** - Browse your photos organized by date
- **Search** - Find photos using Immich's smart search
- **Slideshow** - Start slideshows from any album
- **Video Playback** - Play videos directly in Kodi

## Requirements

- Kodi 19 (Matrix) or later
- A running [Immich](https://immich.app/) server (v1.90.0+)
- An Immich API key

## Installation

### Manual Installation

1. Download the latest release as a ZIP file
2. In Kodi, go to **Add-ons** > **Install from zip file**
3. Navigate to the downloaded ZIP file and select it
4. The addon will be installed

### From Repository (Coming Soon)

The addon will be available in the Kodi addon repository in the future.

## Configuration

### Option 1: Pre-configure with config.txt (Recommended)

For easy setup without typing in Kodi:

1. Before installing, create a `config.txt` file in the addon folder:
   ```
   server_url=https://immich.example.com
   api_key=your-api-key-here
   ```
2. You can copy `config.txt.example` as a template
3. Install the addon - settings will be imported automatically

**Security Note:** The `config.txt` file contains your API key. Don't commit it to version control.

### Option 2: Configure in Kodi Settings

1. Go to **Add-ons** > **My add-ons** > **Picture add-ons** > **Immich**
2. Select **Configure**
3. Enter your settings:

### Required Settings

| Setting | Description |
|---------|-------------|
| **Immich Server URL** | The full URL to your Immich server (e.g., `https://immich.example.com`) |
| **API Key** | Your Immich API key |

### Getting Your API Key

1. Log in to your Immich web interface
2. Click on your profile icon in the top right
3. Go to **Account Settings**
4. Scroll down to **API Keys**
5. Click **New API Key**
6. Give it a name (e.g., "Kodi") and click **Create**
7. Copy the generated key and paste it into the addon settings

## Usage

### Main Menu

When you open the addon, you'll see the following options:

- **My Albums** - Browse albums you've created
- **Shared Albums** - Browse albums shared with you
- **Shared Links** - Access shared links you've created
- **Favorites** - View your favorite photos and videos
- **People** - Browse by recognized faces
- **Timeline** - Browse photos by month
- **Search** - Search your photo library

### Viewing Photos

- Navigate to any album or section
- Select a photo to view it full screen
- Photos open in Kodi's built-in image viewer

### Playing Videos

- Videos are marked in listings
- Select a video to play it in Kodi's video player
- All Kodi video controls work as expected

### Slideshows

- In any album, select **[Start Slideshow]** at the top
- Or right-click any image and select **Start Slideshow from Here**
- Slideshow interval can be configured in settings

## Troubleshooting

### Cannot connect to server

- Verify your server URL is correct and includes the protocol (http:// or https://)
- Ensure your Immich server is running and accessible
- Check that your API key is valid
- If using HTTPS, ensure the certificate is valid

### No albums showing

- Verify your API key has the correct permissions
- Check that you have albums created in Immich
- Try refreshing the view

### Images not loading

- Check your network connection
- Verify the Immich server has the photos available
- Large photos may take time to load

## Development

### Project Structure

```
plugin.image.immich/
├── addon.xml              # Addon metadata
├── default.py             # Main entry point
├── LICENSE
├── README.md
└── resources/
    ├── icon.png           # Addon icon (256x256)
    ├── fanart.png         # Addon fanart
    ├── settings.xml       # Settings definition
    ├── language/
    │   └── resource.language.en_gb/
    │       └── strings.po # English translations
    └── lib/
        ├── __init__.py
        ├── immich_client.py  # Immich API client
        └── plugin.py         # Plugin UI logic
```

### Building

To create a distributable ZIP:

```bash
zip -r plugin.image.immich.zip . -x "*.git*" -x "*.pyc" -x "__pycache__/*"
```

### Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## API Reference

This addon uses the [Immich API](https://immich.app/docs/api/). Key endpoints used:

- `GET /api/albums` - List albums
- `GET /api/albums/{id}` - Get album details
- `GET /api/assets/{id}/thumbnail` - Get asset thumbnail
- `GET /api/assets/{id}/original` - Get original asset
- `GET /api/shared-links` - List shared links
- `POST /api/search/smart` - Smart search

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Immich](https://immich.app/) - The amazing self-hosted photo and video backup solution
- [Kodi](https://kodi.tv/) - The open-source media center
- The Immich and Kodi communities

## Disclaimer

This is an unofficial addon and is not affiliated with Immich or Kodi. Use at your own risk.
