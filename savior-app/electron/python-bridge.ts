import { spawn, ChildProcess } from 'child_process';
import { EventEmitter } from 'events';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';

interface Command {
  id: string;
  type: string;
  action: string;
  params: Record<string, any>;
  timestamp: number;
}

interface Response {
  id: string;
  success: boolean;
  data?: any;
  error?: string;
}

export class PythonBridge extends EventEmitter {
  private pythonProcess: ChildProcess | null = null;
  private commandQueue: Command[] = [];
  private pendingCommands: Map<string, (response: Response) => void> = new Map();
  private buffer: string = '';
  private isReady: boolean = false;
  private saviorPath: string;
  private configDir: string;

  constructor() {
    super();
    // Find the savior module path - use resources in production
    const isProduction = process.env.NODE_ENV === 'production' || !process.defaultApp;

    if (isProduction) {
      // In production, Python files are in Resources folder
      const resourcesPath = process.resourcesPath;
      this.saviorPath = path.join(resourcesPath, 'savior');
    } else {
      // In development, use parent directory
      this.saviorPath = path.join(__dirname, '../../');
    }

    this.configDir = path.join(os.homedir(), '.savior');
  }

  async initialize(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        // Spawn Python process with the bridge script
        const isProduction = process.env.NODE_ENV === 'production' || !process.defaultApp;
        let bridgePath: string;

        // Always use the local path for now during development
        bridgePath = path.join(__dirname, '../python/app_bridge.py');

        // Try to find python3 in common locations
        const pythonPaths = [
          '/opt/anaconda3/bin/python3',
          '/usr/local/bin/python3',
          '/usr/bin/python3',
          '/opt/homebrew/bin/python3',
          'python3'
        ];

        let pythonPath = pythonPaths[0]; // Default to anaconda
        for (const path of pythonPaths) {
          try {
            // Check if it's a command in PATH or an absolute path
            if (path.startsWith('/')) {
              if (fs.existsSync(path)) {
                pythonPath = path;
                break;
              }
            } else {
              // For commands like 'python3', we'll use it directly
              pythonPath = path;
              break;
            }
          } catch (e) {
            // Continue to next path
          }
        }

        console.log('Using Python at:', pythonPath);
        console.log('Bridge script at:', bridgePath);

        this.pythonProcess = spawn(pythonPath, [bridgePath], {
          shell: true,
          cwd: this.saviorPath,
          env: {
            ...process.env,
            PYTHONPATH: this.saviorPath,
            SAVIOR_APP_MODE: 'true'
          }
        });

        this.pythonProcess.stdout?.on('data', (data) => {
          this.handlePythonOutput(data.toString());
        });

        this.pythonProcess.stderr?.on('data', (data) => {
          console.error('Python stderr:', data.toString());
          this.emit('error', { message: data.toString() });
        });

        this.pythonProcess.on('error', (error) => {
          console.error('Failed to start Python process:', error);
          reject(error);
        });

        this.pythonProcess.on('exit', (code) => {
          console.log(`Python process exited with code ${code}`);
          this.isReady = false;
          this.emit('disconnected');

          // Attempt to restart after 5 seconds
          setTimeout(() => {
            this.initialize();
          }, 5000);
        });

        // Wait for ready signal
        this.once('ready', () => {
          this.isReady = true;
          resolve();
        });

        // Timeout after 10 seconds
        setTimeout(() => {
          if (!this.isReady) {
            reject(new Error('Python bridge initialization timeout'));
          }
        }, 10000);

      } catch (error) {
        reject(error);
      }
    });
  }

  private handlePythonOutput(data: string) {
    this.buffer += data;
    const lines = this.buffer.split('\n');

    // Keep the last incomplete line in the buffer
    this.buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.trim()) {
        try {
          const message = JSON.parse(line);
          this.processMessage(message);
        } catch (error) {
          console.error('Failed to parse Python output:', line);
        }
      }
    }
  }

  private processMessage(message: any) {
    switch (message.type) {
      case 'ready':
        this.emit('ready');
        break;

      case 'response':
        const callback = this.pendingCommands.get(message.id);
        if (callback) {
          callback(message);
          this.pendingCommands.delete(message.id);
        }
        break;

      case 'event':
        this.handleEvent(message);
        break;

      case 'log':
        console.log('Python log:', message.message);
        break;

      default:
        console.warn('Unknown message type:', message.type);
    }
  }

  private handleEvent(event: any) {
    switch (event.name) {
      case 'projects_updated':
        this.emit('projects-updated', event.data);
        break;

      case 'backup_started':
        this.emit('backup-started', event.data);
        break;

      case 'backup_completed':
        this.emit('backup-completed', event.data);
        break;

      case 'backup_progress':
        this.emit('backup-progress', event.data);
        break;

      case 'daemon_status':
        this.emit('daemon-status', event.data);
        break;

      case 'error':
        this.emit('error', event.data);
        break;

      default:
        this.emit(event.name, event.data);
    }
  }

  sendCommand(action: string, params: Record<string, any> = {}): Promise<Response> {
    return new Promise((resolve, reject) => {
      const command: Command = {
        id: this.generateId(),
        type: 'command',
        action,
        params,
        timestamp: Date.now()
      };

      if (!this.isReady) {
        reject(new Error('Python bridge not ready'));
        return;
      }

      this.pendingCommands.set(command.id, resolve);

      // Send command to Python process
      this.pythonProcess?.stdin?.write(JSON.stringify(command) + '\n');

      // Timeout after 30 seconds
      setTimeout(() => {
        if (this.pendingCommands.has(command.id)) {
          this.pendingCommands.delete(command.id);
          reject(new Error(`Command timeout: ${action}`));
        }
      }, 30000);
    });
  }

  async getProjects(): Promise<any[]> {
    const response = await this.sendCommand('get_projects');
    return response.data || [];
  }

  async getBackups(projectPath: string): Promise<any[]> {
    const response = await this.sendCommand('get_backups', { path: projectPath });
    return response.data || [];
  }

  async watchProject(projectPath: string, options: any = {}): Promise<void> {
    await this.sendCommand('watch', { path: projectPath, ...options });
  }

  async stopProject(projectPath: string): Promise<void> {
    await this.sendCommand('stop', { path: projectPath });
  }

  async saveBackup(projectPath: string, description: string): Promise<void> {
    await this.sendCommand('save', { path: projectPath, description });
  }

  async restoreBackup(projectPath: string, backupId: string, options: any = {}): Promise<void> {
    await this.sendCommand('restore', {
      path: projectPath,
      backup_id: backupId,
      ...options
    });
  }

  async getDaemonStatus(): Promise<any> {
    const response = await this.sendCommand('daemon_status');
    return response.data;
  }

  async startDaemon(): Promise<void> {
    await this.sendCommand('daemon_start');
  }

  async stopDaemon(): Promise<void> {
    await this.sendCommand('daemon_stop');
  }

  startMonitoring(): void {
    // Start periodic status updates
    setInterval(async () => {
      if (this.isReady) {
        try {
          await this.sendCommand('refresh_status');
        } catch (error) {
          console.error('Failed to refresh status:', error);
        }
      }
    }, 5000); // Every 5 seconds
  }

  shutdown(): void {
    if (this.pythonProcess) {
      this.sendCommand('shutdown').catch(() => {});
      setTimeout(() => {
        this.pythonProcess?.kill();
        this.pythonProcess = null;
      }, 1000);
    }
  }

  private generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
}