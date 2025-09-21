# Savior Features & Advanced Usage 🛟

## Table of Contents
- [New Features](#new-features)
- [Command Reference](#command-reference)
- [Compression Options](#compression-options)
- [Tree Visualization](#tree-visualization)
- [Disk Space Management](#disk-space-management)
- [Progress Indicators](#progress-indicators)
- [Help System](#help-system)

## New Features

### 📊 Compression Control
Savior now supports adjustable compression levels from 0 (no compression) to 9 (maximum compression).

```bash
# No compression - fastest, largest files
savior save "Quick save" --compression 0

# Maximum compression - slowest, smallest files
savior save "Compressed save" --compression 9

# Default balanced compression (level 6)
savior save "Normal save"
```

**When to use different compression levels:**
- **Level 0**: When speed is critical and disk space isn't a concern
- **Levels 1-3**: Fast compression with reasonable size reduction
- **Levels 4-6**: Balanced performance (default is 6)
- **Levels 7-9**: Maximum compression when storage space is limited

### 🌳 Project Tree Visualization

View your project structure with the `tree` command:

```bash
# Basic tree view
savior tree

# Control depth and details
savior tree --depth 5 --no-size

# Exclude specific patterns
savior tree --exclude-git --ignore "*.pyc,__pycache__"

# Show all files including ignored ones
savior tree --all
```

**Tree Options:**
- `--depth N` or `-d N`: Maximum depth to display (default: 3)
- `--no-size`: Hide file sizes for cleaner output
- `--exclude-git`: Don't show .git directory
- `--ignore PATTERNS`: Additional comma-separated patterns to ignore
- `--all` or `-a`: Show ignored files too

### 💾 Disk Space Protection

Savior automatically checks available disk space before creating backups:
- Requires at least 10% free space OR estimated backup size + 100MB
- Estimates compressed backup size (~40% of original)
- Prevents backup failures due to insufficient space

Error handling:
```bash
# If insufficient space:
✗ Backup failed: Insufficient disk space. Available: 2.5GB, Required: 5.0GB
```

### 📈 Progress Bars

Visual feedback during backup operations:

```bash
# Backups show progress
savior save "Large backup"
Creating backup: 100%|██████████| 2547/2547 [00:03<00:00, 847.23files/s]

# Disable for scripts/automation
savior save "Automated backup" --no-progress
```

## Command Reference

### Core Commands

#### `savior watch`
Start auto-saving with enhanced options:
```bash
savior watch --compression 7 --tree --exclude-git
```

**New flags:**
- `--compression N`: Set compression level (0-9)
- `--tree`: Show project structure before starting
- `--exclude-git`: Exclude .git from backups

#### `savior save`
Manual backup with new features:
```bash
savior save "Description" --compression 9 --tree --no-progress
```

**New flags:**
- `--compression N`: Compression level (0-9, default: 6)
- `--tree`: Preview what will be backed up
- `--no-progress`: Disable progress bar

#### `savior tree`
Visualize project structure:
```bash
savior tree --depth 4 --exclude-git --ignore "node_modules,*.log"
```

### Help Commands

#### `savior help` / `savior`
Show general help. Running `savior` without arguments now shows help.

#### `savior commands` / `savior cmds`
Display organized command list with descriptions:
```bash
savior commands

Core Commands:
  watch                Start auto-saving current directory
  save                 Force a save right now
  restore              See all backups and restore one
  ...
```

#### `savior flags`
Show all available flags for all commands:
```bash
savior flags

Savior Flags & Options:
============================================================

savior watch:
  --interval N              Backup interval in minutes (default: 20)
  --compression N           Compression level 0-9 (default: 6)
  --tree                    Show project tree before starting
  ...
```

## Compression Options

### Compression Levels Explained

| Level | Speed | Size | Use Case |
|-------|-------|------|----------|
| 0 | Instant | Largest | Quick temporary backups |
| 1-3 | Very Fast | Large | Development snapshots |
| 4-6 | Balanced | Medium | **Default - general use** |
| 7-8 | Slow | Small | Long-term storage |
| 9 | Slowest | Smallest | Archival/limited space |

### File Extensions
- Compressed backups: `.tar.gz`
- Uncompressed backups: `.tar`

### Performance Impact
```bash
# Example on a 100MB project:
--compression 0: ~100MB backup, <1 second
--compression 6: ~40MB backup, ~2 seconds
--compression 9: ~35MB backup, ~5 seconds
```

## Tree Visualization

### Understanding the Tree Output

```
Project/ (1.5MB)                    # Root with total size
├── src/ (850KB)                    # Directory with contents size
│   ├── main.py (15KB)              # File with size
│   └── utils/ (20KB)               # Subdirectory
│       └── helper.py (20KB)
└── README.md (10KB)
```

### Filtering Options

```bash
# Exclude common build artifacts
savior tree --ignore "*.pyc,__pycache__,node_modules,dist,build"

# Deep inspection
savior tree --depth 10

# Clean output without sizes
savior tree --no-size

# Include everything (even ignored files)
savior tree --all
```

## Disk Space Management

### Automatic Space Checking
Before each backup, Savior:
1. Estimates the compressed backup size
2. Checks available disk space
3. Ensures sufficient space (10% free or needed + 100MB)
4. Provides clear error messages if space is insufficient

### Space-Saving Tips

```bash
# Use higher compression
savior watch --compression 9

# Exclude unnecessary files
savior watch --exclude-git --ignore "*.mp4,*.mov,node_modules"

# Clean old backups
savior purge --keep 5

# Check current usage
savior paths  # Shows storage used
```

## Progress Indicators

### Progress Bar Features
- Shows files processed in real-time
- Displays rate (files/second)
- Estimates time remaining for large backups
- Can be disabled with `--no-progress`

### When to Disable Progress
```bash
# In automated scripts
savior save "Automated" --no-progress

# In CI/CD pipelines
savior save "CI Build" --no-progress

# When logging output
savior save "Logged" --no-progress >> backup.log
```

## Advanced Examples

### Complete Backup Strategy
```bash
# Development: Fast, frequent backups
savior watch --interval 10 --compression 3

# Production: Compressed, excluding artifacts
savior watch --compression 8 --exclude-git --ignore "dist,build,*.log"

# Archival: Maximum compression, full tree check
savior tree --depth 10
savior save "Archive $(date +%Y-%m-%d)" --compression 9
```

### Scripting and Automation
```bash
#!/bin/bash
# Backup script with error handling

# Check space and preview
savior tree --depth 2 --no-size

# Create backup without progress
if savior save "Automated backup" --compression 7 --no-progress; then
    echo "Backup successful"
else
    echo "Backup failed" >&2
    exit 1
fi
```

### Project Analysis
```bash
# Analyze project structure
savior tree --depth 5 > project_structure.txt

# Check what would be backed up
savior tree --exclude-git --ignore "*.tmp,cache"

# Compare with actual backup
savior save "Test" --tree --compression 0
```

## Performance Considerations

### Compression Trade-offs
- **CPU Usage**: Higher compression uses more CPU
- **I/O Impact**: Uncompressed backups write more data
- **Time**: Level 0 is ~10x faster than level 9
- **Space**: Level 9 saves ~60-70% vs uncompressed

### Best Practices
1. Use default compression (6) for most cases
2. Use `--no-progress` in scripts
3. Exclude large binary files that don't compress well
4. Run `savior purge` periodically to manage space
5. Use `savior tree` to understand what's being backed up

## Troubleshooting

### Common Issues

**Insufficient disk space:**
```bash
# Check available space
df -h .

# Clean old backups
savior purge --keep 3

# Use higher compression
savior save "Compressed" --compression 9
```

**Slow backups:**
```bash
# Use lower compression
savior watch --compression 2

# Exclude large files
savior watch --ignore "*.mp4,*.zip,node_modules"

# Check what's being backed up
savior tree --depth 3
```

**Finding help:**
```bash
# General help
savior help

# Command-specific help
savior save --help

# See all flags
savior flags

# List all commands
savior commands
```