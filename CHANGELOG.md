# Changelog

All notable changes to Savior will be documented in this file.

## [1.0.0] - 2024-01-17

### Added
- 🧟 **Zombie dead code detection** - Find unused functions, classes, and variables
  - Confidence scoring (definitely/probably/possibly dead)
  - Dynamic usage detection (getattr, eval, API endpoints)
  - Quarantine system to safely isolate dead code
  - Runtime tracing for verification
- ☁️ **Cloud backup support** (self-hosted)
  - MinIO, Backblaze B2, Wasabi, local NAS support
  - Interactive setup wizard
  - Sync, list, download commands
- 🔧 **Background daemon** for multi-project support
- 📊 **Smart activity detection** - Waits for 2 seconds of inactivity
- 📦 **Incremental backups** - Only save changes to reduce storage
- 🔍 **Enhanced diff command** with color-coded output
- 🙏 **Pray command** for deep recovery (searches everywhere)
- ✨ **Partial restore** - Restore only specific files
- 🧪 **Test suite** with pytest
- 🚀 **CI/CD pipeline** with GitHub Actions

### Changed
- Improved CLI messages and descriptions
- Better error handling throughout

### Fixed
- Various edge cases in backup restoration
- Ignore patterns now work correctly

## [1.0.0] - 2024-01-01

### Added
- Initial release
- Basic backup every 20 minutes
- Simple restore functionality
- .saviorignore support