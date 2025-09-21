import { exec, spawn, ChildProcess } from 'child_process';
import { EventEmitter } from 'events';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';
import { FSWatcher, watch } from 'chokidar';

export class SaviorBridge extends EventEmitter {
  private saviorCommand: string = 'savior';
  private sessionProcesses: Map<string, ChildProcess>;
  private watchedProjects: Map<string, any>;
  private fileWatchers: Map<string, FSWatcher>;
  private modifiedFiles: Map<string, Map<string, Date>>; // projectPath -> Map of filepath -> lastModified

  constructor() {
    super();
    this.sessionProcesses = new Map();
    this.watchedProjects = new Map();
    this.fileWatchers = new Map();
    this.modifiedFiles = new Map();
    this.findSaviorCommand();
  }

  private checkProjectOverlap(newPath: string, existingProjects: any[]): any[] {
    const overlaps = [];
    const normalizedNewPath = path.resolve(newPath);

    for (const project of existingProjects) {
      const normalizedExistingPath = path.resolve(project.path);

      // Check if new path is inside existing project
      if (normalizedNewPath.startsWith(normalizedExistingPath + path.sep) ||
          normalizedNewPath === normalizedExistingPath) {
        overlaps.push({
          type: 'child',
          existingPath: project.path,
          existingName: project.name,
          message: `This folder is inside "${project.name}" which is already being watched.`
        });
      }
      // Check if existing project is inside new path
      else if (normalizedExistingPath.startsWith(normalizedNewPath + path.sep)) {
        overlaps.push({
          type: 'parent',
          existingPath: project.path,
          existingName: project.name,
          message: `This folder contains "${project.name}" which is already being watched.`
        });
      }
    }

    return overlaps;
  }

  private findSaviorCommand() {
    const isDev = process.env.NODE_ENV === 'development';
    const { app } = require('electron');

    console.log('[DEBUG] findSaviorCommand called');
    console.log('[DEBUG] isDev:', isDev);
    console.log('[DEBUG] app.isPackaged:', app.isPackaged);
    console.log('[DEBUG] process.resourcesPath:', process.resourcesPath);

    if (!isDev && app.isPackaged) {
      // Production: Use the bundled Python files
      const resourcesPath = process.resourcesPath;
      // Use launcher.py instead of cli.py for better import handling
      const saviorPath = path.join(resourcesPath, 'savior', 'launcher.py');
      const pythonDepsPath = path.join(resourcesPath, 'python-deps');

      console.log('[DEBUG] Production mode detected');
      console.log('[DEBUG] Looking for bundled savior at:', saviorPath);
      console.log('[DEBUG] Python deps path:', pythonDepsPath);
      console.log('[DEBUG] File exists?', fs.existsSync(saviorPath));
      console.log('[DEBUG] Deps exist?', fs.existsSync(pythonDepsPath));

      if (fs.existsSync(saviorPath)) {
        // Check if python3 is available
        exec('which python3', (pythonError, pythonStdout) => {
          console.log('[DEBUG] which python3 result:');
          console.log('[DEBUG]   error:', pythonError ? pythonError.message : 'none');
          console.log('[DEBUG]   stdout:', pythonStdout ? pythonStdout.trim() : 'none');

          if (!pythonError && pythonStdout) {
            // Set PYTHONPATH to include our bundled dependencies
            const pythonPath = `PYTHONPATH="${pythonDepsPath}:${resourcesPath}/savior:$PYTHONPATH"`;
            this.saviorCommand = `${pythonPath} python3 "${saviorPath}"`;
            console.log('[DEBUG] ✓ Set saviorCommand with PYTHONPATH to:', this.saviorCommand);
          } else {
            // Try /usr/bin/python3 as fallback
            console.log('[DEBUG] Checking /usr/bin/python3...');
            if (fs.existsSync('/usr/bin/python3')) {
              const pythonPath = `PYTHONPATH="${pythonDepsPath}:${resourcesPath}/savior:$PYTHONPATH"`;
              this.saviorCommand = `${pythonPath} /usr/bin/python3 "${saviorPath}"`;
              console.log('[DEBUG] ✓ Using /usr/bin/python3 with PYTHONPATH:', this.saviorCommand);
            } else {
              console.error('[DEBUG] ✗ Python3 not found! App may not work correctly.');
              // Last resort: try python
              const pythonPath = `PYTHONPATH="${pythonDepsPath}:${resourcesPath}/savior:$PYTHONPATH"`;
              this.saviorCommand = `${pythonPath} python "${saviorPath}"`;
              console.log('[DEBUG] Using fallback python command:', this.saviorCommand);
            }
          }
        });
      } else {
        console.error('[DEBUG] ✗ Bundled savior NOT FOUND at:', saviorPath);
        console.log('[DEBUG] Attempting fallback to system savior...');
        // Fall back to trying system savior
        exec('which savior', (error, stdout) => {
          console.log('[DEBUG] which savior result:', error ? 'error' : stdout?.trim());
          if (!error && stdout) {
            this.saviorCommand = stdout.trim();
            console.log('[DEBUG] ✓ Falling back to system savior:', this.saviorCommand);
          } else {
            console.error('[DEBUG] ✗ No savior command found anywhere!');
          }
        });
      }
    } else {
      // Development mode: Try to find system savior first
      console.log('[DEBUG] Development mode - looking for savior');
      exec('which savior', (error, stdout) => {
        console.log('[DEBUG] which savior result:', error ? 'error' : stdout?.trim());
        if (!error && stdout) {
          this.saviorCommand = stdout.trim();
          console.log('[DEBUG] ✓ Found system savior at:', this.saviorCommand);
        } else {
          // Try to use the local development version
          const localPath = path.join(__dirname, '../../savior/launcher.py');
          console.log('[DEBUG] Checking local path:', localPath);
          console.log('[DEBUG] Local file exists?', fs.existsSync(localPath));
          if (fs.existsSync(localPath)) {
            this.saviorCommand = `python3 "${localPath}"`;
            console.log('[DEBUG] ✓ Using local savior at:', this.saviorCommand);
          } else {
            console.error('[DEBUG] ✗ No local savior found!');
          }
        }
      });
    }
  }

  async getProjects(): Promise<any[]> {
    console.log('[DEBUG] ========== getProjects START ==========');
    console.log('[DEBUG] Current saviorCommand:', this.saviorCommand);
    console.log('[DEBUG] Current watchedProjects map size:', this.watchedProjects.size);

    // Log all tracked projects
    if (this.watchedProjects.size > 0) {
      console.log('[DEBUG] Tracked projects in map:');
      this.watchedProjects.forEach((data, path) => {
        console.log(`[DEBUG]   - ${path}: active=${data.active}, pid=${data.pid}`);
      });
    }

    // Wait a bit if saviorCommand is not yet set
    if (!this.saviorCommand || this.saviorCommand === 'savior') {
      console.log('[DEBUG] Command not ready, waiting 500ms...');
      await new Promise(resolve => setTimeout(resolve, 500));
      console.log('[DEBUG] After wait, command is:', this.saviorCommand);
    }

    return new Promise((resolve) => {
      const statusCmd = `${this.saviorCommand} daemon status`;
      console.log('[DEBUG] Executing daemon status command:', statusCmd);

      exec(statusCmd, (error, stdout, stderr) => {
        console.log('[DEBUG] Daemon status execution complete');
        if (error) {
          // If error, no daemon running or no projects
          console.log('[DEBUG] Daemon status ERROR:', error.message);
          console.log('[DEBUG] Daemon stderr:', stderr);
        } else {
          console.log('[DEBUG] Daemon status SUCCESS');
        }

        console.log('[DEBUG] Daemon stdout (raw):');
        console.log(stdout || '(empty)');
        console.log('[DEBUG] --- End of daemon output ---');

        // Parse daemon status output
        const projects: any[] = [];
        const lines = stdout ? stdout.split('\n') : [];
        console.log('[DEBUG] Parsing daemon output:', lines.length, 'lines');

        // Look for watched projects section
        const watchedIndex = lines.findIndex(line => line.includes('Watched Projects:'));
        console.log('[DEBUG] Looking for "Watched Projects:" section...');

        if (watchedIndex === -1) {
          console.log('[DEBUG] No "Watched Projects:" section found in daemon output');
          console.log('[DEBUG] Will rely on watchedProjects map only');
        } else {
          console.log('[DEBUG] Found "Watched Projects:" at line', watchedIndex);

          // Parse each project line (starts with • )
          for (let i = watchedIndex + 1; i < lines.length; i++) {
          const line = lines[i];
          if (line.includes('•')) {
            // Extract path from line like: "  • /Users/noahedery/Desktop/Savior"
            const pathMatch = line.match(/•\s+(.+)$/);
            if (pathMatch) {
              const projectPath = pathMatch[1].trim();

              // Get additional info from next lines
              let pid = null;
              let mode = 'smart, incremental';
              let started = null;

              // Check next lines for details
              if (i + 1 < lines.length && lines[i + 1].includes('Started:')) {
                const startMatch = lines[i + 1].match(/Started:\s+(.+)$/);
                if (startMatch) started = startMatch[1].trim();
              }

              if (i + 2 < lines.length && lines[i + 2].includes('PID:')) {
                const pidMatch = lines[i + 2].match(/PID:\s+(\d+)/);
                if (pidMatch) pid = pidMatch[1];

                const modeMatch = lines[i + 2].match(/\(([^)]+)\)/);
                if (modeMatch) mode = modeMatch[1];

                i += 2; // Skip the lines we already processed
              }

              const projectData = {
                id: projects.length,
                path: projectPath,
                name: path.basename(projectPath),
                active: true,
                pid: pid,
                mode: mode,
                started: started,
                fileCount: 0,
                lastBackup: null,
                persistence: 'always',  // Daemon projects are always persistent
                nextBackup: null as string | null,
                watchInterval: null
              };

              // Try to read metadata for next backup time
              try {
                const metadataPath = path.join(projectPath, '.savior', 'metadata.json');
                if (fs.existsSync(metadataPath)) {
                  const metadata = JSON.parse(fs.readFileSync(metadataPath, 'utf-8'));
                  projectData.watchInterval = metadata.watch_interval || 20;

                  // Calculate next backup time
                  if (metadata.backups && metadata.backups.length > 0) {
                    const lastBackup = metadata.backups[metadata.backups.length - 1];
                    projectData.lastBackup = lastBackup.timestamp;

                    // Calculate next backup based on last backup + interval
                    const lastBackupTime = new Date(lastBackup.timestamp);
                    const intervalMs = (projectData.watchInterval || 20) * 60 * 1000;
                    const nextBackupTime = new Date(lastBackupTime.getTime() + intervalMs);
                    projectData.nextBackup = nextBackupTime.toISOString();

                    console.log('[DEBUG] Calculated next backup for', projectPath);
                    console.log('[DEBUG]   Last backup:', lastBackup.timestamp);
                    console.log('[DEBUG]   Interval:', projectData.watchInterval, 'minutes');
                    console.log('[DEBUG]   Next backup:', projectData.nextBackup);
                  } else if (started) {
                    // If no backups yet, calculate from start time
                    const startTime = new Date(started);
                    const intervalMs = (projectData.watchInterval || 20) * 60 * 1000;
                    const nextBackupTime = new Date(startTime.getTime() + intervalMs);
                    projectData.nextBackup = nextBackupTime.toISOString();

                    console.log('[DEBUG] No backups yet, calculated from start time');
                    console.log('[DEBUG]   Started:', started);
                    console.log('[DEBUG]   Next backup:', projectData.nextBackup);
                  }
                }
              } catch (err) {
                console.log('[SaviorBridge] Could not read metadata for', projectPath);
              }

              projects.push(projectData);
            }
          }
        }
        } // Close the else block from line 180

        console.log('[DEBUG] Projects parsed from daemon:', projects.length);

        // Add tracked projects that might not show up in daemon status
        console.log('[DEBUG] Checking watchedProjects map for additional projects...');
        console.log('[DEBUG] Map size:', this.watchedProjects.size);

        this.watchedProjects.forEach((projectData, projectPath) => {
          console.log('[DEBUG] Checking tracked project:', projectPath);
          const existingProjectIndex = projects.findIndex(p => p.path === projectPath);

          if (existingProjectIndex === -1) {
            console.log('[DEBUG] Project not in daemon list, adding from map:', projectPath);
            projects.push({
              ...projectData,
              id: projects.length
            });
            console.log('[DEBUG] ✓ Added tracked project to list');
          } else {
            // Merge tracked data with daemon data, preserving important fields from tracked data
            console.log('[DEBUG] Project already in list, merging data');
            const existingProject = projects[existingProjectIndex];
            projects[existingProjectIndex] = {
              ...existingProject,
              nextBackup: projectData.nextBackup || existingProject.nextBackup,
              watchInterval: projectData.watchInterval || existingProject.watchInterval,
              lastBackup: projectData.lastBackup || existingProject.lastBackup
            };
            console.log('[DEBUG] ✓ Merged tracked data for', projectPath);
          }
        });

        console.log('[DEBUG] Total projects after adding tracked:', projects.length);

        // Also check for standalone watch processes - including Python processes
        exec('ps aux | grep -E "(savior watch|cli.py watch)" | grep -v grep', (psError, psOut) => {
          if (!psError && psOut) {
            console.log('[SaviorBridge] Found standalone watch processes:');
            console.log(psOut);

            // Parse standalone processes
            const lines = psOut.split('\n').filter(l => l.trim());
            lines.forEach(line => {
              // For now, skip parsing ps output as we can't reliably get project path
              // We rely on our watchedProjects map instead
              console.log('[SaviorBridge] Found process line:', line);
            });
          }

          console.log('[DEBUG] ========== FINAL PROJECT LIST ==========');
          console.log('[DEBUG] Total projects:', projects.length);
          projects.forEach(p => {
            console.log(`[DEBUG]   - ${p.path} (active=${p.active}, pid=${p.pid})`);
          });
          console.log('[DEBUG] ========================================');

          console.log('[DEBUG] Emitting projects-updated event');
          this.emit('projects-updated', projects);
          console.log('[DEBUG] Resolving getProjects promise');
          resolve(projects);
        });
      });
    });
  }

  async watchProject(projectPath: string, options: any = {}): Promise<void> {
    console.log('[DEBUG] ========== watchProject START ==========');
    console.log('[DEBUG] Project path:', projectPath);
    console.log('[DEBUG] Options:', JSON.stringify(options, null, 2));
    console.log('[DEBUG] Current saviorCommand:', this.saviorCommand);

    // Wait for command to be ready
    if (!this.saviorCommand || this.saviorCommand === 'savior') {
      console.log('[DEBUG] Command not ready, waiting 1000ms...');
      await new Promise(resolve => setTimeout(resolve, 1000));
      console.log('[DEBUG] After wait, command is:', this.saviorCommand);
    }

    // Check for overlapping projects
    console.log('[DEBUG] Checking for overlapping projects...');
    const projects = await this.getProjects();
    console.log('[DEBUG] Current projects count:', projects.length);
    const overlaps = this.checkProjectOverlap(projectPath, projects);

    if (overlaps.length > 0) {
      // Return overlap info instead of proceeding
      const error = new Error('PROJECT_OVERLAP');
      (error as any).overlaps = overlaps;
      (error as any).newPath = projectPath;
      throw error;
    }

    return new Promise((resolve, reject) => {
      // Build command options from config
      const daemonArgs = [`"${projectPath}"`];
      const watchArgs: string[] = []; // savior watch doesn't take path - uses cwd!

      if (options.interval) {
        daemonArgs.push(`--interval ${options.interval}`);
        watchArgs.push('--interval', options.interval.toString());
      }

      if (options.smartMode === false) {
        daemonArgs.push('--no-smart');
        watchArgs.push('--no-smart');
      }

      if (options.incremental === false) {
        daemonArgs.push('--full');
        watchArgs.push('--full');
      }

      if (options.excludeGit) {
        daemonArgs.push('--exclude-git');
        watchArgs.push('--exclude-git');
      }

      if (options.compression !== undefined) {
        watchArgs.push('--compression', options.compression.toString());
        // Note: daemon add doesn't support compression level yet
      }

      // Check persistence setting - only use daemon if "always"
      const useDaemon = options.persistence === 'always' || options.persistence === undefined;

      if (useDaemon) {
        // First try daemon add for persistent watching
        const daemonCmd = `${this.saviorCommand} daemon add ${daemonArgs.join(' ')}`;
        console.log('[SaviorBridge] Attempting daemon command (persistent):', daemonCmd);

        // If persistence is "always", also add to auto-launch
        if (options.persistence === 'always') {
          const autolaunchCmd = `${this.saviorCommand} autolaunch add-project "${projectPath}" --interval ${options.interval || 20}${options.smartMode !== false ? ' --smart' : ''}`;
          console.log('[SaviorBridge] Adding to auto-launch:', autolaunchCmd);
          exec(autolaunchCmd, (autoError, autoOut) => {
            if (!autoError && autoOut.includes('✓')) {
              console.log('[SaviorBridge] Project added to auto-launch');
            }
          });
        }

      exec(daemonCmd, (error, stdout, stderr) => {
        console.log('[SaviorBridge] Daemon command completed');
        console.log('[SaviorBridge] - Error object:', error ? error.message : 'none');
        console.log('[SaviorBridge] - Stdout:', stdout || '(empty)');
        console.log('[SaviorBridge] - Stderr:', stderr || '(empty)');

        // Check for errors in both error object AND stdout/stderr
        const hasError = error ||
                        (stdout && stdout.includes('✗')) ||
                        (stdout && stdout.includes('Exception')) ||
                        (stdout && stdout.includes('Failed')) ||
                        (stderr && stderr.length > 0);

        console.log('[SaviorBridge] Has error?', hasError);

        if (hasError) {
          console.error('[SaviorBridge] DAEMON ADD FAILED - USING FALLBACK');
          console.log('[SaviorBridge] Falling back to direct watch command');

          // Fall back to direct watch command
          const watchCmd = [this.saviorCommand, 'watch', ...watchArgs].join(' ');
          console.log('[SaviorBridge] Running fallback watch command:', watchCmd);

          // Try spawning with inherited stdio first to see output
          const watchProcess = spawn(this.saviorCommand, ['watch', ...watchArgs], {
            detached: true,
            stdio: ['ignore', 'pipe', 'pipe'], // Capture stdout/stderr for debugging
            cwd: projectPath
          });

          // Log any immediate output
          watchProcess.stdout?.on('data', (data) => {
            console.log('[SaviorBridge] Watch stdout:', data.toString());
          });
          watchProcess.stderr?.on('data', (data) => {
            console.log('[SaviorBridge] Watch stderr:', data.toString());
          });

          watchProcess.on('error', (err) => {
            console.error('[SaviorBridge] Watch process error:', err);
          });

          watchProcess.on('exit', (code) => {
            console.log('[SaviorBridge] Watch process exited with code:', code);
          });

          watchProcess.unref();

          console.log('[SaviorBridge] Watch process spawned with PID:', watchProcess.pid);
          console.log('[SaviorBridge] Started watching project with direct watch');
          console.log('[SaviorBridge] Project:', projectPath);
          console.log('[SaviorBridge] Options:', JSON.stringify(options, null, 2));

          // Track this project immediately
          const now = new Date();
          const intervalMs = (options.interval || 20) * 60 * 1000;
          const nextBackupTime = new Date(now.getTime() + intervalMs);

          const projectData = {
            path: projectPath,
            name: path.basename(projectPath),
            active: true,
            pid: watchProcess.pid,
            mode: options.smartMode === false ? 'basic' : 'smart, incremental',
            started: now.toISOString(),
            fileCount: 0,
            lastBackup: null,
            persistence: options.persistence || 'always',
            nextBackup: nextBackupTime.toISOString(),
            watchInterval: options.interval || 20
          };

          console.log('[DEBUG] Adding to watchedProjects map:');
          console.log('[DEBUG]   Path:', projectPath);
          console.log('[DEBUG]   PID:', watchProcess.pid);
          console.log('[DEBUG]   Mode:', projectData.mode);
          this.watchedProjects.set(projectPath, projectData);
          console.log('[DEBUG] ✓ Project tracked! Map size now:', this.watchedProjects.size);

          // Start file watcher for this project
          this.startFileWatcher(projectPath);

          // Give it a moment to start, then refresh project list
          setTimeout(() => {
            console.log('[SaviorBridge] Waiting 2 seconds for watch to start...');
            console.log('[SaviorBridge] Now refreshing project list');
            this.getProjects().then(projects => {
              console.log('[SaviorBridge] Refreshed! Found projects:', projects.length);
              if (projects.length > 0) {
                console.log('[SaviorBridge] Project paths:', projects.map(p => p.path));
              }
              this.emit('projects-updated', projects);
              resolve();
            }).catch(err => {
              console.error('[SaviorBridge] Error refreshing projects:', err);
              resolve(); // Still resolve to avoid hanging
            });
          }, 2000);
          return;
        }

        console.log('[SaviorBridge] DAEMON ADD SUCCEEDED (no error detected)');
        console.log('[SaviorBridge] Daemon output:', stdout || '(empty)');

        // Track this project
        const now = new Date();
        const intervalMs = (options.interval || 20) * 60 * 1000;
        const nextBackupTime = new Date(now.getTime() + intervalMs);

        const projectData = {
          path: projectPath,
          name: path.basename(projectPath),
          active: true,
          pid: 'daemon',
          mode: options.smartMode === false ? 'basic' : 'smart, incremental',
          started: now.toISOString(),
          fileCount: 0,
          lastBackup: null,
          persistence: options.persistence || 'always',
          nextBackup: nextBackupTime.toISOString(),
          watchInterval: options.interval || 20
        };

        console.log('[DEBUG] Adding daemon project to watchedProjects map:');
        console.log('[DEBUG]   Path:', projectPath);
        console.log('[DEBUG]   Mode:', projectData.mode);
        this.watchedProjects.set(projectPath, projectData);
        console.log('[DEBUG] ✓ Daemon project tracked! Map size now:', this.watchedProjects.size);

        // Start file watcher for this project
        this.startFileWatcher(projectPath);

        // Refresh project list
        this.getProjects().then(projects => {
          console.log('[SaviorBridge] Updated projects count:', projects.length);
          this.emit('projects-updated', projects);
          resolve();
        }).catch(err => {
          console.error('[SaviorBridge] Error refreshing projects:', err);
          reject(err);
        });
      });
      } else {
        // Session-only mode - always use direct watch command
        console.log('[SaviorBridge] Using session-only mode, spawning direct watch process');

        const watchCmd = [this.saviorCommand, 'watch', ...watchArgs].join(' ');
        console.log('[SaviorBridge] Running session-only watch command:', watchCmd);

        const watchProcess = spawn(this.saviorCommand, ['watch', ...watchArgs], {
          detached: true,
          stdio: ['ignore', 'pipe', 'pipe'],
          cwd: projectPath
        });

        watchProcess.stdout?.on('data', (data) => {
          console.log('[SaviorBridge] Session watch stdout:', data.toString());
        });
        watchProcess.stderr?.on('data', (data) => {
          console.log('[SaviorBridge] Session watch stderr:', data.toString());
        });

        watchProcess.on('error', (err) => {
          console.error('[SaviorBridge] Session watch process error:', err);
        });

        watchProcess.on('exit', (code) => {
          console.log('[SaviorBridge] Session watch process exited with code:', code);
        });

        watchProcess.unref();

        console.log('[SaviorBridge] Session watch process spawned with PID:', watchProcess.pid);

        // Store session processes so we can stop them on app quit
        if (!this.sessionProcesses) {
          this.sessionProcesses = new Map();
        }
        this.sessionProcesses.set(projectPath, watchProcess);

        // Give it a moment to start, then refresh project list
        setTimeout(() => {
          this.getProjects().then(projects => {
            this.emit('projects-updated', projects);
            resolve();
          });
        }, 2000);
      }
    });
  }

  async stopProject(projectPath: string): Promise<void> {
    return new Promise((resolve) => {
      // Stop file watcher
      this.stopFileWatcher(projectPath);

      // Remove from tracked projects
      this.watchedProjects.delete(projectPath);
      console.log('[SaviorBridge] Removed from tracked projects:', projectPath);

      // Check if it's a session process first
      const sessionProcess = this.sessionProcesses.get(projectPath);
      if (sessionProcess) {
        console.log('Stopping session watch process for:', projectPath);
        try {
          process.kill(sessionProcess.pid!);
          this.sessionProcesses.delete(projectPath);
        } catch (err) {
          console.error('Error killing session process:', err);
        }
        // Refresh project list
        setTimeout(() => {
          this.getProjects().then(projects => {
            this.emit('projects-updated', projects);
          });
          resolve();
        }, 500);
        return;
      }

      // Also remove from auto-launch if it was there
      const removeAutolaunchCmd = `${this.saviorCommand} autolaunch remove-project "${projectPath}"`;
      console.log('[SaviorBridge] Removing from auto-launch:', removeAutolaunchCmd);
      exec(removeAutolaunchCmd, (autoError) => {
        if (!autoError) {
          console.log('[SaviorBridge] Project removed from auto-launch');
        }
      });

      // Otherwise, try to remove from daemon
      exec(`${this.saviorCommand} daemon remove "${projectPath}"`, (error) => {
        if (error) {
          console.error('Error removing from daemon, trying to stop direct watch:', error);

          // Try to find and kill the direct watch process
          // Get the PID from daemon status output
          exec(`${this.saviorCommand} daemon status`, (statusError, statusOut) => {
            if (!statusError && statusOut) {
              const lines = statusOut.split('\n');
              let foundPid = null;

              for (let i = 0; i < lines.length; i++) {
                if (lines[i].includes(projectPath)) {
                  // Look for PID in next lines
                  for (let j = i + 1; j < Math.min(i + 3, lines.length); j++) {
                    const pidMatch = lines[j].match(/PID:\s+(\d+)/);
                    if (pidMatch) {
                      foundPid = pidMatch[1];
                      break;
                    }
                  }
                  break;
                }
              }

              if (foundPid) {
                console.log(`Killing watch process with PID ${foundPid} for ${projectPath}`);
                exec(`kill ${foundPid}`, (killError) => {
                  if (killError) {
                    console.error('Error killing process:', killError);
                  }
                });
              }
            }

            // Refresh project list after attempting to stop
            setTimeout(() => {
              this.getProjects().then(projects => {
                this.emit('projects-updated', projects);
              });
              resolve();
            }, 1000);
          });
        } else {
          console.log('Project removed from daemon:', projectPath);
          // Refresh project list
          this.getProjects().then(projects => {
            this.emit('projects-updated', projects);
          });
          resolve();
        }
      });
    });
  }

  async getBackups(projectPath: string): Promise<any[]> {
    return new Promise((resolve) => {
      exec(`${this.saviorCommand} list ${projectPath} --json`, (error, stdout) => {
        if (error) {
          console.error('Error getting backups:', error);
          resolve([]);
          return;
        }

        try {
          const backups = JSON.parse(stdout);
          resolve(backups);
        } catch (e) {
          // Parse non-JSON output
          const lines = stdout.split('\n').filter(line => line.trim());
          const backups = lines.map((line, index) => {
            const parts = line.split(/\s+/);
            return {
              id: index,
              timestamp: parts[0] || new Date().toISOString(),
              description: parts.slice(1).join(' ') || 'Backup',
              size: 0
            };
          });
          resolve(backups);
        }
      });
    });
  }

  async restoreBackup(projectPath: string, backupId: string | number): Promise<void> {
    return new Promise((resolve, reject) => {
      exec(`${this.saviorCommand} restore ${projectPath} ${backupId} --force`, (error) => {
        if (error) {
          reject(error);
          return;
        }
        this.emit('restore-completed', { path: projectPath, backupId });
        resolve();
      });
    });
  }

  async saveBackup(projectPath: string, description: string): Promise<void> {
    return new Promise((resolve, reject) => {
      console.log('[DEBUG] saveBackup called for:', projectPath);
      console.log('[DEBUG] Description:', description);

      // The savior backup command should be run in the project directory
      // Format: cd to directory && savior backup
      const backupCmd = `cd "${projectPath}" && ${this.saviorCommand} save "${description}"`;
      console.log('[DEBUG] Running backup command:', backupCmd);

      exec(backupCmd, (error, stdout, stderr) => {
        if (error) {
          console.error('[DEBUG] Backup command failed:', error);
          console.error('[DEBUG] stderr:', stderr);
          console.error('[DEBUG] stdout:', stdout);
          reject(error);
          return;
        }

        console.log('[DEBUG] Backup succeeded!');
        console.log('[DEBUG] stdout:', stdout);

        // Update the next backup time for this project
        const now = new Date();
        const project = this.watchedProjects.get(projectPath);
        if (project) {
          const intervalMs = (project.watchInterval || 20) * 60 * 1000;
          const nextBackupTime = new Date(now.getTime() + intervalMs);
          project.lastBackup = now.toISOString();
          project.nextBackup = nextBackupTime.toISOString();
          this.watchedProjects.set(projectPath, project);
        }

        this.emit('backup-completed', {
          path: projectPath,
          description,
          timestamp: now.toISOString()
        });
        resolve();
      });
    });
  }

  async getStatus(): Promise<any> {
    return new Promise((resolve) => {
      exec(`${this.saviorCommand} status --json`, (error, stdout) => {
        if (error) {
          resolve({ running: false, projects: [] });
          return;
        }

        try {
          const status = JSON.parse(stdout);
          resolve(status);
        } catch (e) {
          resolve({ running: true, projects: [] });
        }
      });
    });
  }

  async removeProjectsAndWatch(projectsToRemove: string[], newPath: string, options: any = {}): Promise<void> {
    console.log('[SaviorBridge] Removing overlapping projects and adding new one');

    // Remove each overlapping project
    for (const projectPath of projectsToRemove) {
      await this.stopProject(projectPath);
    }

    // Add the new project without overlap check
    return new Promise((resolve, reject) => {
      // Build command options from config
      const daemonArgs = [`"${newPath}"`];
      const watchArgs: string[] = [];

      if (options.interval) {
        daemonArgs.push(`--interval ${options.interval}`);
        watchArgs.push('--interval', options.interval.toString());
      }

      if (options.smartMode === false) {
        daemonArgs.push('--no-smart');
        watchArgs.push('--no-smart');
      }

      if (options.incremental === false) {
        daemonArgs.push('--full');
        watchArgs.push('--full');
      }

      if (options.excludeGit) {
        daemonArgs.push('--exclude-git');
        watchArgs.push('--exclude-git');
      }

      if (options.compression !== undefined) {
        watchArgs.push('--compression', options.compression.toString());
      }

      // First try daemon add
      const daemonCmd = `${this.saviorCommand} daemon add ${daemonArgs.join(' ')}`;
      console.log('[SaviorBridge] Attempting daemon command:', daemonCmd);

      exec(daemonCmd, (error, stdout, stderr) => {
        const hasError = error ||
                        (stdout && stdout.includes('✗')) ||
                        (stdout && stdout.includes('Exception')) ||
                        (stdout && stdout.includes('Failed')) ||
                        (stderr && stderr.length > 0);

        if (hasError) {
          // Fall back to direct watch command
          const watchProcess = spawn(this.saviorCommand, ['watch', ...watchArgs], {
            detached: true,
            stdio: ['ignore', 'pipe', 'pipe'],
            cwd: newPath
          });

          watchProcess.unref();
          console.log('[SaviorBridge] Started watching with direct watch');

          setTimeout(() => {
            this.getProjects().then(projects => {
              this.emit('projects-updated', projects);
              resolve();
            });
          }, 2000);
          return;
        }

        // Refresh project list
        this.getProjects().then(projects => {
          this.emit('projects-updated', projects);
          resolve();
        });
      });
    });
  }

  private startFileWatcher(projectPath: string): void {
    console.log('[DEBUG] Starting file watcher for:', projectPath);

    // Stop existing watcher if any
    if (this.fileWatchers.has(projectPath)) {
      this.fileWatchers.get(projectPath)?.close();
    }

    // Initialize modified files map for this project
    if (!this.modifiedFiles.has(projectPath)) {
      this.modifiedFiles.set(projectPath, new Map());
    }

    // Create file watcher with chokidar
    const watcher = watch(projectPath, {
      ignored: [
        /(^|[\/\\])\../, // Hidden files
        /node_modules/,
        /.git/,
        /.savior/,
        /\.pyc$/,
        /__pycache__/,
        /\.DS_Store/,
        /build/,
        /dist/,
        /\.log$/
      ],
      persistent: true,
      ignoreInitial: true,
      depth: 10,
      awaitWriteFinish: {
        stabilityThreshold: 1000,
        pollInterval: 100
      }
    });

    // Handle file changes
    watcher.on('change', (filePath: string) => {
      const relativePath = path.relative(projectPath, filePath);
      const modifiedFiles = this.modifiedFiles.get(projectPath);

      if (modifiedFiles) {
        modifiedFiles.set(relativePath, new Date());

        // Keep only last 20 modified files
        if (modifiedFiles.size > 20) {
          const oldest = Array.from(modifiedFiles.entries())
            .sort((a, b) => a[1].getTime() - b[1].getTime())[0];
          modifiedFiles.delete(oldest[0]);
        }

        console.log('[DEBUG] File modified:', relativePath, 'in project:', projectPath);

        // Emit file change event
        this.emit('file-changed', {
          projectPath,
          filePath: relativePath,
          timestamp: new Date(),
          allModifiedFiles: Array.from(modifiedFiles.entries()).map(([file, date]) => ({
            path: file,
            timestamp: date
          }))
        });
      }
    });

    // Handle new files
    watcher.on('add', (filePath: string) => {
      const relativePath = path.relative(projectPath, filePath);
      const modifiedFiles = this.modifiedFiles.get(projectPath);

      if (modifiedFiles) {
        modifiedFiles.set(relativePath, new Date());

        console.log('[DEBUG] File added:', relativePath, 'in project:', projectPath);

        this.emit('file-changed', {
          projectPath,
          filePath: relativePath,
          timestamp: new Date(),
          allModifiedFiles: Array.from(modifiedFiles.entries()).map(([file, date]) => ({
            path: file,
            timestamp: date
          }))
        });
      }
    });

    watcher.on('error', (error: any) => {
      console.error('[DEBUG] File watcher error for', projectPath, ':', error);
    });

    this.fileWatchers.set(projectPath, watcher);
    console.log('[DEBUG] File watcher started for:', projectPath);
  }

  private stopFileWatcher(projectPath: string): void {
    const watcher = this.fileWatchers.get(projectPath);
    if (watcher) {
      console.log('[DEBUG] Stopping file watcher for:', projectPath);
      watcher.close();
      this.fileWatchers.delete(projectPath);
      this.modifiedFiles.delete(projectPath);
    }
  }

  getModifiedFiles(projectPath: string): Array<{path: string, timestamp: Date}> {
    const modifiedFiles = this.modifiedFiles.get(projectPath);
    if (!modifiedFiles) return [];

    return Array.from(modifiedFiles.entries())
      .map(([file, date]) => ({ path: file, timestamp: date }))
      .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
  }

  shutdown(): void {
    // Stop all file watchers
    this.fileWatchers.forEach((watcher, path) => {
      console.log(`Stopping file watcher for ${path}`);
      watcher.close();
    });
    this.fileWatchers.clear();
    this.modifiedFiles.clear();

    // Stop all session processes
    console.log('Stopping all session watch processes...');
    this.sessionProcesses.forEach((process, path) => {
      try {
        console.log(`Killing session process for ${path}`);
        process.kill();
      } catch (err) {
        console.error(`Error killing session process for ${path}:`, err);
      }
    });
    this.sessionProcesses.clear();

    // Stop the daemon
    exec(`${this.saviorCommand} daemon stop`, (error) => {
      if (error) {
        console.error('Error stopping daemon:', error);
      } else {
        console.log('Daemon stopped');
      }
    });
  }
}