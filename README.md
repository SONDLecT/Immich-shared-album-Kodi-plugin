# Immich Kodi Addons

> **⚠️ Work in Progress**: This project is under active development. Features may be incomplete or change. Feedback and contributions welcome!

Kodi addons to browse, view, and display photos from your [Immich](https://immich.app/) self-hosted photo server.

## Addons Included

| Addon | Description |
|-------|-------------|
| **plugin.image.immich** | Browse and view your Immich photo library in Kodi |
| **screensaver.immich** | Photo screensaver that displays images from Immich |

---

## Plugin: Browse Immich Library

### Features

- **Browse Albums** - View your personal albums
- **Shared Albums** - Access albums shared with you by other users
- **Shared Links** - Browse shared links you've created
- **Favorites** - Quick access to your favorite photos and videos
- **People** - Browse photos by recognized faces
- **Timeline** - Browse your photos organized by date
- **Search** - Find photos using Immich's smart search
- **Slideshow** - Start slideshows from any album or person
- **Video Playback** - Play videos directly in Kodi

---

## Screensaver: Immich Photos

A beautiful screensaver that displays photos from your Immich server.

### Features

- **Multiple Photo Sources**:
  - Random photos from entire library
  - Specific album
  - All shared albums
  - Specific people (supports multiple!)
  - Favorites only
- **Photo Info Overlay** - Shows filename, date, and location
- **Configurable Display Time** - 3-60 seconds per photo
- **Multiple Person Selection** - Comma-separated person IDs for family slideshows

---

## Requirements

- Kodi 19 (Matrix) or later
- A running [Immich](https://immich.app/) server (v1.90.0+)
- An Immich API key
- **For Apple HEIC photos**: Install the "HEIF image decoder" addon from Kodi's official repository

## Installation

### Step 1: Clone or Download

```bash
git clone https://github.com/SONDLecT/Immich-shared-album-Kodi-plugin
cd Immich-shared-album-Kodi-plugin
```

### Step 2: Configure

Create your `config.txt` file with your Immich credentials:

```bash
# For the plugin
cp config.txt.example config.txt
nano config.txt  # Add your server_url and api_key

# For the screensaver (uses same format)
cp config.txt screensaver.immich/config.txt
```

Example `config.txt`:
```
server_url=https://immich.example.com
api_key=your-api-key-here
```

### Step 3: Build ZIP Files

```bash
# Build the plugin
mkdir -p plugin.image.immich
cp addon.xml default.py LICENSE README.md config.txt plugin.image.immich/
cp -r resources plugin.image.immich/
zip -r plugin.image.immich.zip plugin.image.immich

# Build the screensaver
cd screensaver.immich
mkdir -p ../screensaver.immich.zip.tmp
cp -r * ../screensaver.immich.zip.tmp/
cd ..
mv screensaver.immich.zip.tmp screensaver.immich-pkg
zip -r screensaver.immich.zip screensaver.immich-pkg
rm -rf screensaver.immich-pkg
```

### Step 4: Install in Kodi

1. Go to **Add-ons** → **Install from zip file**
2. Navigate to the ZIP file and select it
3. Repeat for both addons if desired

### Step 5: Install HEIF Decoder (for Apple Photos)

If you have HEIC photos from Apple devices:

1. Go to **Add-ons** → **Install from repository**
2. Select **All repositories** → **Image decoder**
3. Install **HEIF image decoder**

## Getting Your API Key

1. Log in to your Immich web interface
2. Click on your profile icon → **Account Settings**
3. Scroll to **API Keys** → **New API Key**
4. Name it (e.g., "Kodi") and click **Create**
5. Copy the key to your `config.txt`

### Recommended API Permissions

For basic browsing, your API key needs:
- `album.read` - Browse albums
- `asset.read` - View photos/videos
- `asset.download` - Download images for display
- `person.read` - Browse by people
- `sharedLink.read` - Access shared links

## Usage

### Plugin

- Open the Immich addon from **Add-ons** → **Picture add-ons**
- Browse albums, people, timeline, etc.
- Click any photo to view full screen
- Use **[Start Slideshow]** option in albums

### Screensaver

1. Go to **Settings** → **Interface** → **Screensaver**
2. Select **Immich Photos** as your screensaver
3. Configure photo source in screensaver settings:
   - Choose source: Random, Specific Album, Shared Albums, Specific People, or Favorites
   - Use **"Browse Albums..."** or **"Browse People..."** buttons to select
   - Multiple people can be selected for family slideshows

## Troubleshooting

### Cannot connect to server
- Verify your server URL includes protocol (http:// or https://)
- Ensure your Immich server is running and accessible
- Check that your API key is valid

### HEIC images not displaying
- Install the **HEIF image decoder** addon from Kodi's official repository
- The addon will show a notification if it's missing

### Images loading slowly
- First-time image loads require downloading to cache
- Subsequent views are faster (cached locally)

### No albums/photos showing
- Verify your API key has correct permissions
- Check that you have content in Immich

## Project Structure

```
Immich-shared-album-Kodi-plugin/
├── plugin.image.immich/          # Main browsing plugin
│   ├── addon.xml
│   ├── default.py
│   └── resources/
│       ├── lib/
│       │   ├── immich_client.py
│       │   └── plugin.py
│       └── settings.xml
│
└── screensaver.immich/           # Photo screensaver
    ├── addon.xml
    ├── entrypoint.py
    └── resources/
        ├── lib/
        │   ├── immich_client.py
        │   └── screensaver.py
        ├── skins/default/1080i/
        │   └── screensaver-immich.xml
        └── settings.xml
```

## Contributing

Contributions welcome! This is a work in progress.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file.

## Acknowledgments

- [Immich](https://immich.app/) - Self-hosted photo/video backup
- [Kodi](https://kodi.tv/) - Open-source media center
- [screensaver.kaster](https://github.com/enen92/screensaver.kaster) - Screensaver reference

## Disclaimer

Unofficial addon, not affiliated with Immich or Kodi. Use at your own risk.
