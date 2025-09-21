# Savior Desktop App 🛟

A beautiful, native desktop application for Savior that seamlessly integrates with the CLI version.

## Features

- **Visual Dashboard**: See all your projects and their backup status at a glance
- **Real-time Monitoring**: Live updates when backups are created
- **Backup Timeline**: Browse and restore from any backup with a click
- **Settings Panel**: Configure backup preferences through an intuitive UI
- **System Tray Integration**: Runs quietly in the background
- **Cross-platform**: Works on macOS, Windows, and Linux
- **CLI Compatibility**: Works seamlessly with existing Savior CLI installations

## Architecture

The app uses a hybrid architecture:
- **Electron + React + TypeScript**: Modern, responsive UI
- **Python Bridge**: Direct integration with existing Savior Python code
- **IPC Communication**: Real-time updates between processes
- **Shared Configuration**: Uses same `~/.savior/` directory as CLI

## Development

### Prerequisites
- Node.js 16+
- Python 3.7+
- Savior CLI installed

### Setup
```bash
# Install dependencies
npm install

# Run in development mode
npm run dev

# In another terminal, start Electron
npm run electron-dev
```

### Building

```bash
# Build for current platform
npm run dist

# Build for specific platforms
npm run dist:mac
npm run dist:win
npm run dist:linux
```

## Project Structure

```
savior-app/
├── electron/           # Electron main process
│   ├── main.ts        # Main window & app lifecycle
│   ├── preload.ts     # Preload script for IPC
│   ├── python-bridge.ts # Python process management
│   └── ipc/           # IPC handlers
├── src/               # React app
│   ├── components/    # UI components
│   ├── stores/        # Zustand state management
│   ├── utils/         # Utility functions
│   └── App.tsx        # Main app component
├── python/            # Python integration
│   └── app_bridge.py  # Bridge to Savior CLI
└── assets/           # Icons and resources
```

## Key Components

### ProjectList
Displays all watched projects with:
- Active/inactive status
- Last backup time
- Storage usage
- Quick actions (start/stop, force backup)

### BackupViewer
Timeline view of backups with:
- Backup metadata
- Restore functionality
- Preview capability
- Delete option

### SettingsPanel
Configure:
- Backup intervals
- Compression levels
- Smart mode
- Theme preferences
- Cloud sync settings

### Python Bridge
- Spawns Python subprocess
- Handles command execution
- Emits real-time events
- Manages daemon communication

## CLI Integration

The app works seamlessly with the CLI:
- Shares the same configuration (`~/.savior/`)
- Can be used alongside CLI commands
- Updates reflect in both interfaces
- Daemon is shared between app and CLI

## Customization

### Themes
The app supports dark and light themes, configurable in Settings.

### Tray Menu
Right-click the tray icon for quick access to:
- Project list
- Start/stop watching
- Force backups
- Preferences

## Troubleshooting

### App won't start
- Ensure Python 3.7+ is installed
- Check that Savior CLI is in the parent directory
- Look for errors in the console

### Python bridge errors
- Verify Savior modules are importable
- Check Python path configuration
- Ensure proper permissions on `~/.savior/`

### Build issues
- Clear `node_modules` and reinstall
- Check webpack configuration
- Ensure all TypeScript types are resolved

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test on all platforms
5. Submit a pull request

## License

MIT - Same as Savior CLI

## Support

For issues or questions, open an issue on GitHub or contact the maintainers.