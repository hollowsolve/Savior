<p align="center">
  <img src="Savior.png" alt="Savior Logo" width="200">
</p>

# Savior 🛟

Automatic backups for developers who break things

## Quickstart

```bash
# Install
pip install savior

# Start protecting your work
cd my-project
savior watch

# That's it. You're protected.
```

## What is Savior?

Savior is a dead-simple backup tool that automatically saves your work every 20 minutes. When you inevitably break something at 3am, Savior has your back with instant restore points.

**Not a git replacement** - It's your safety net that backs up everything, including git history

## Installation

### From PyPI (Coming Soon)
```bash
pip install savior
```

### From Source
```bash
git clone https://github.com/hollowsolve/Savior.git
cd Savior
pip install -e .
```

## Usage

Start watching a project:
```bash
savior watch
```

That's literally it. Savior now saves your project every 20 minutes.

## Commands

### Basic Commands
- `savior watch` - Start auto-saving with smart mode & incremental backups (default)
  - `--no-smart` - Disable smart mode (save even during typing)
  - `--full` - Use full backups instead of incremental
  - `--exclude-git` - Exclude .git directory to save space
  - `--compression N` - Set compression level (0=none, 9=max, default: 6)
  - `--tree` - Show project structure before starting
  - `--cloud` - Enable automatic cloud backup syncing 🆕
- `savior save "description"` - Force a save right now
  - `--compression N` - Set compression level (0-9)
  - `--tree` - Preview what will be backed up
  - `--no-progress` - Disable progress bar
- `savior restore` - See all backups and restore one
  - `--files "*.py"` - Restore only specific files
  - `--preview` - See what would be restored without doing it
- `savior tree` - Visualize project structure 🆕
  - `--depth N` - Maximum depth to display
  - `--exclude-git` - Hide .git directory
  - `--ignore "*.pyc,node_modules"` - Additional patterns to ignore
- `savior stop` - Stop watching
- `savior status` - Check if Savior is running
- `savior list` - Show all saved backups
- `savior purge` - Delete old backups to free space

### Help & Discovery 🆕
- `savior help` - Show help (or just run `savior`)
- `savior commands` / `savior cmds` - Show organized command list
- `savior flags` - Show all available flags for all commands

### Cloud Backup 🆕
- `savior cloud setup` - Configure cloud storage (AWS S3, Google Cloud, Azure, MinIO, etc.)
- `savior cloud sync` - Manually sync local backups with cloud
  - `--upload-only` - Only upload to cloud
  - `--download-only` - Only download from cloud
- `savior cloud list` - List all cloud backups
- `savior cloud download <backup>` - Download specific backup from cloud

### Advanced Recovery
- `savior diff` - Compare backups to see what changed
  - `--show-content` - Show actual file differences
- `savior resurrect [filename]` - Find and restore deleted files
- `savior pray` - 🙏 Deep recovery attempt (searches everywhere)
  - `--restore` - Auto-restore found files

### Daemon & Multi-Project
- `savior daemon start` - Start background daemon
- `savior daemon stop` - Stop daemon
- `savior daemon status` - See all watched projects
- `savior daemon add ~/project1 ~/project2` - Watch multiple projects
- `savior daemon remove ~/project1` - Stop watching a project
- `savior projects --all` - List all Savior projects on your system

### 🧟 Dead Code Detection
- `savior zombie scan` - Find unused functions and classes
  - `--verbose` - Show detailed analysis
  - `--json output.json` - Export results
- `savior zombie check <name>` - Check if specific code is dead
- `savior zombie stats` - Show dead code percentage

## Key Features

- 🎯 **Zero Configuration** - Just run `savior watch` and you're protected
- ☁️ **Cloud Backup Support** - Auto-sync to AWS S3, Google Cloud, Azure, or self-hosted 🆕
- 💾 **Incremental Backups (Default)** - Only saves changes, keeping storage minimal
- 🧠 **Smart Mode (Default)** - Waits for inactivity before saving
- 🗜️ **Adjustable Compression** - Control backup size vs speed (levels 0-9)
- 📊 **Progress Indicators** - Visual feedback during backup operations
- 🌳 **Tree Visualization** - See your project structure at a glance
- 💽 **Disk Space Protection** - Automatic space checking before backups
- 🧟 **Dead Code Detection** - Built-in zombie scanner finds unused code
- 🙏 **Deep Recovery** - Resurrect files from editor swaps, trash, and git stashes
- 📊 **Multi-Project Support** - Watch multiple projects with a single daemon

## Examples

### Basic Usage
```bash
$ savior watch
✓ Savior is now watching your project
✓ Will save after 20 minutes of work + 2 seconds of inactivity

[... 2 hours later after you broke everything ...]

$ savior restore
Available backups:
1. 10 minutes ago - "working on new feature"
2. 30 minutes ago - "before I tried that sketchy regex"
3. 50 minutes ago - "everything worked here"
4. 70 minutes ago - "initial backup"

Which backup? > 3
✓ Restored to 50 minutes ago!
```

### New: Compression & Tree View
```bash
# See what will be backed up
$ savior tree --depth 2
Project Structure:
my-project/ (45.2MB)
├── src/ (30.1MB)
│   ├── main.py (15.2KB)
│   └── utils/ (2.3MB)
└── tests/ (5.1MB)

# Create highly compressed backup
$ savior save "before deployment" --compression 9
Creating backup: 100%|██████████| 1547/1547 [00:02<00:00]
✓ Saved backup: "before deployment"
  Size: 12.3 MB (compressed from 45.2MB)
  Compression: level 9
```

### Cloud Backup Setup & Usage
```bash
# Configure cloud storage
$ savior cloud setup
🌥️  Savior Cloud Setup Wizard
========================================

Choose your storage provider:
1. AWS S3
2. Google Cloud Storage
3. Azure Blob Storage
4. MinIO (self-hosted S3)
5. Backblaze B2
6. Wasabi
7. Local NAS/Network Drive
8. Custom S3-compatible

Enter choice (1-8): 1
AWS Access Key ID: AKIAIOSFODNN7EXAMPLE
AWS Secret Access Key: ****
AWS Region (default: us-east-1): us-west-2
Bucket name (default: savior-backups): my-backups
Encrypt backups? (y/n): y
Auto-sync with cloud after each backup? (y/n): y

✓ Configuration saved to ~/.savior/cloud.conf
  Run 'savior cloud sync' to start syncing!

# Watch with automatic cloud sync
$ savior watch --cloud
✓ Savior is now watching your project
☁️ Cloud sync enabled
✓ Will save after 20 minutes of work + 2 seconds of inactivity
☁️ Backups will auto-sync to cloud storage

[... after backup ...]
✓ Backup saved: 20241018_143022.tar.gz
  Size: 12.3 MB
  Type: Incremental
  ☁️ Uploaded to cloud storage

# Manual cloud sync
$ savior cloud sync
☁️  Syncing with cloud storage...
✓ Uploaded 3 new backups to cloud
✓ Downloaded 2 backups from cloud
✓ Sync complete!

# List cloud backups
$ savior cloud list
☁️  Cloud backups for my-project:
  1. 20241018_143022.tar.gz - 12.3 MB - 10 minutes ago
  2. 20241018_141522.tar.gz - 11.8 MB - 30 minutes ago
  3. 20241018_135022.tar.gz - 45.2 MB - 50 minutes ago
```

### Basic Mode (No Smart Detection)
```bash
$ savior watch --no-smart --full
✓ Savior is now watching your project (basic mode)
✓ Backups every 20 minutes to .savior/
✓ Backup saved (45.2 MB)
```

### Deep Recovery When All Hope Is Lost
```bash
$ savior pray
🙏 Initiating deep recovery prayer sequence...

RECOVERY SCAN RESULTS:
================
✓ Editor swap files found: 3
  - .main.py.swp (2 minutes ago)
✓ Items in trash: 2
  - old_config.json (1 hour ago)
✓ Git stashes found: 1
  - stash@{0}: WIP on main: fixed critical bug

Use --restore flag to attempt automatic restoration
```

### Watch Multiple Projects with Daemon
```bash
# Start the daemon
$ savior daemon start
✓ Savior daemon started

# Add multiple projects (uses smart + incremental by default)
$ savior daemon add ~/project1 ~/project2 ~/project3

# Include git history in backups
$ savior daemon add ~/critical-project --include-git
✓ Added /home/user/project1 (PID: 12345)
✓ Added /home/user/project2 (PID: 12346)
✓ Added /home/user/project3 (PID: 12347)

# Check status
$ savior daemon status
Savior Daemon Status:
  PID: 12344
  Projects watched: 3

Watched Projects:
  • /home/user/project1
    Started: 2024-01-01T10:00:00
    PID: 12345 (smart, incremental)
  • /home/user/project2
    Started: 2024-01-01T10:00:01
    PID: 12346 (smart, incremental)
```

### Compare What Changed
```bash
$ savior diff --show-content
Comparing 10 minutes ago with current files...

Added files (2):
  + src/new_feature.py
  + tests/test_feature.py

Modified files (3):
  ~ main.py
  ~ config.json
  ~ README.md

File: main.py
-    return calculate_total(items)
+    return calculate_total(items, tax_rate=0.08)
```

### Find Dead Code with Zombie
```bash
$ savior zombie scan
🧟 Starting ZOMBIE scan...
   Analyzing your codebase for dead code...

🧟 ZOMBIE CODE SCAN REPORT
============================================================
Total dead code: 437 lines
Files affected: 12

📦 Dead Functions (23)
----------------------------------------
  • calculate_legacy_tax (45 lines)
    src/utils/calculations.py:127
  • format_old_response (32 lines)
    src/handlers/legacy.py:89
  • validate_deprecated_input (28 lines)
    src/validators/old.py:15

🏗️ Dead Classes (3)
----------------------------------------
  • OldConfigManager (87 lines)
    src/config/deprecated.py:45
  • LegacyProcessor (62 lines)
    src/processing/old.py:12

⚠️  Found 26 potential zombie definitions
   437 lines of potentially dead code

$ savior zombie check calculate_legacy_tax
Checking 'calculate_legacy_tax'...

✓ 'calculate_legacy_tax' is defined in:
  • src/utils/calculations.py

⚠️  'calculate_legacy_tax' is never referenced - might be dead code!
```

## Why Savior?

- **When git is overkill** - Not every experiment needs version control
- **Before risky changes** - Auto-saves before you try that "clever" regex
- **Learning projects** - Focus on coding, not commit messages
- **Prototype safety** - Quick ideas deserve backups too
- **Disaster recovery** - When `git reset --hard` goes wrong

## .saviorignore

Create a `.saviorignore` file to skip files:
```
node_modules/
*.pyc
__pycache__/
.DS_Store
*.log
build/
dist/
# Add .git/ here if you want to ignore it even with --include-git
# .git/
```

## Storage & Performance

**Minimal footprint:**
- First backup: ~10MB compressed (100MB project)
- Incremental saves: 1-2MB each
- 30 days of history: ~500MB total
- Binary files >100MB: Referenced, not copied

**Compression Options:** 🆕
- Level 0: No compression (fastest)
- Level 6: Default balanced compression
- Level 9: Maximum compression (smallest files)
- Automatic disk space checking prevents failures

**Smart cleanup:**
- Keeps all backups < 24 hours
- Transitions to hourly → daily → weekly
- Auto-removes backups > 30 days old
- Always keeps 10 most recent backups

## FAQ

**How is this different from git?**
Git manages versions. Savior prevents disasters. Use both.

**Does it work with git?**
Yes! By default, Savior ignores .git/ to save space. Use `--include-git` to backup git history too.

**What if I'm actively coding?**
Smart mode waits for 2 seconds of inactivity.

**Can I force a backup?**
`savior save "before risky change"`

**What about sensitive files?**
Add them to `.saviorignore` just like `.gitignore`

## License

MIT - Do whatever you want with it

## Requirements

- Python 3.7+
- Works on Linux, macOS, Windows
- ~50MB for Savior + backup storage

## Documentation

📚 **[See FEATURES.md for detailed documentation of all features](FEATURES.md)**

Includes:
- Complete command reference
- Compression guide and benchmarks
- Tree visualization options
- Disk space management
- Advanced examples and workflows

## Contributing

PRs welcome! Keep it simple - Savior should just work.

---

**Made with ❤️ by Noah Edery**

**Remember:** The best backup is the one you don't have to think about.
