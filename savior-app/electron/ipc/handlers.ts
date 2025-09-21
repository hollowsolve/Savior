import { ipcMain, dialog, shell, app } from 'electron';
import { SaviorBridge } from '../savior-bridge';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';
import { spawn } from 'child_process';

export function setupIpcHandlers(saviorBridge: SaviorBridge) {
  console.log('[DEBUG IPC] Setting up IPC handlers');

  // Projects
  ipcMain.handle('get-projects', async () => {
    console.log('[DEBUG IPC] get-projects called');
    const projects = await saviorBridge.getProjects();
    console.log('[DEBUG IPC] get-projects returning', projects.length, 'projects');
    return projects;
  });

  ipcMain.handle('watch-project', async (_, path: string, options: any) => {
    console.log('[IPC] watch-project called with path:', path);
    console.log('[IPC] Options:', options);
    try {
      const result = await saviorBridge.watchProject(path, options);
      console.log('[IPC] watch-project succeeded');
      return result;
    } catch (error: any) {
      console.error('[IPC] watch-project failed:', error);
      if (error.message === 'PROJECT_OVERLAP') {
        // Return overlap info to renderer
        return {
          error: 'PROJECT_OVERLAP',
          overlaps: error.overlaps,
          newPath: error.newPath
        };
      }
      throw error; // Re-throw to send to renderer
    }
  });

  ipcMain.handle('remove-and-watch', async (_, projectsToRemove: string[], newPath: string, options: any) => {
    console.log('[IPC] remove-and-watch called');
    console.log('[IPC] Projects to remove:', projectsToRemove);
    console.log('[IPC] New path:', newPath);
    console.log('[IPC] Options:', options);
    try {
      const result = await saviorBridge.removeProjectsAndWatch(projectsToRemove, newPath, options);
      console.log('[IPC] remove-and-watch succeeded');
      return result;
    } catch (error: any) {
      console.error('[IPC] remove-and-watch failed:', error);
      throw error;
    }
  });

  ipcMain.handle('stop-project', async (_, path: string) => {
    return await saviorBridge.stopProject(path);
  });

  ipcMain.handle('add-project', async (_, projectPath: string) => {
    return await saviorBridge.watchProject(projectPath);
  });

  ipcMain.handle('remove-project', async (_, projectPath: string) => {
    return await saviorBridge.stopProject(projectPath);
  });

  // Backups
  ipcMain.handle('get-backups', async (_, projectPath: string) => {
    return await saviorBridge.getBackups(projectPath);
  });

  ipcMain.handle('save-backup', async (_, projectPath: string, description: string) => {
    return await saviorBridge.saveBackup(projectPath, description);
  });

  ipcMain.handle('restore-backup', async (_, projectPath: string, backupId: string, options: any) => {
    return await saviorBridge.restoreBackup(projectPath, backupId);
  });

  ipcMain.handle('compare-backups', async (_, projectPath: string, backup1: string, backup2: string) => {
    // Not implemented yet in savior CLI
    return [];
  });

  ipcMain.handle('delete-backup', async (_, projectPath: string, backupId: string) => {
    // Not implemented yet in savior CLI
    return { success: true };
  });

  // Settings
  ipcMain.handle('get-settings', async () => {
    const configPath = path.join(os.homedir(), '.savior', 'app_settings.json');

    try {
      if (fs.existsSync(configPath)) {
        const content = fs.readFileSync(configPath, 'utf-8');
        return JSON.parse(content);
      }
    } catch (error) {
      console.error('Failed to read settings:', error);
    }

    // Return default settings
    return {
      theme: 'dark',
      autoStart: false,
      notifications: true,
      interval: 20,
      compression: 6,
      smartMode: true,
      incremental: true,
      excludeGit: false,
      cloudSync: false,
      showInDock: true,
      minimizeToTray: true
    };
  });

  ipcMain.handle('update-settings', async (_, settings: any) => {
    const configDir = path.join(os.homedir(), '.savior');
    const configPath = path.join(configDir, 'app_settings.json');

    try {
      // Ensure config directory exists
      if (!fs.existsSync(configDir)) {
        fs.mkdirSync(configDir, { recursive: true });
      }

      fs.writeFileSync(configPath, JSON.stringify(settings, null, 2));

      // Apply some settings immediately
      if (settings.showInDock !== undefined) {
        if (process.platform === 'darwin' && app.dock) {
          if (settings.showInDock) {
            app.dock.show();
          } else {
            app.dock.hide();
          }
        }
      }

      return { success: true };
    } catch (error: any) {
      console.error('Failed to save settings:', error);
      return { success: false, error: error?.message || 'Failed to save settings' };
    }
  });

  // Cloud
  ipcMain.handle('get-cloud-status', async () => {
    // Not implemented yet
    return { connected: false };
  });

  ipcMain.handle('setup-cloud', async (_, config: any) => {
    // Not implemented yet
    return { success: false };
  });

  ipcMain.handle('sync-cloud', async (_, projectPath?: string) => {
    // Not implemented yet
    return { success: false };
  });

  // Daemon
  ipcMain.handle('get-daemon-status', async () => {
    return await saviorBridge.getStatus();
  });

  // File monitoring
  ipcMain.handle('get-modified-files', async (_, projectPath: string) => {
    console.log('[DEBUG IPC] get-modified-files called for:', projectPath);
    return saviorBridge.getModifiedFiles(projectPath);
  });

  ipcMain.handle('start-daemon', async () => {
    // Start watching all projects
    const projects = await saviorBridge.getProjects();
    for (const project of projects) {
      await saviorBridge.watchProject(project.path);
    }
    return { success: true };
  });

  ipcMain.handle('stop-daemon', async () => {
    saviorBridge.shutdown();
    return { success: true };
  });

  // System
  ipcMain.handle('open-in-editor', async (_, filePath: string) => {
    // Try to open in VS Code first, then default editor
    try {
      await shell.openPath(filePath);
    } catch (error) {
      console.error('Failed to open in editor:', error);
    }
  });

  ipcMain.handle('show-in-folder', async (_, filePath: string) => {
    shell.showItemInFolder(filePath);
  });

  ipcMain.handle('select-directory', async () => {
    console.log('[IPC] select-directory called - Opening folder dialog');
    const result = await dialog.showOpenDialog({
      properties: ['openDirectory'],
      title: 'Select Project Directory'
    });

    if (!result.canceled && result.filePaths.length > 0) {
      console.log('[IPC] Folder selected:', result.filePaths[0]);
      return result.filePaths[0];
    }

    console.log('[IPC] Folder selection cancelled by user');
    return null;
  });

  // Backup Contents Viewer
  ipcMain.handle('get-backup-contents', async (_, args: { backupPath: string }) => {
    console.log('[IPC] get-backup-contents called for:', args.backupPath);

    return new Promise((resolve) => {
      const pythonScriptPath = app.isPackaged
        ? path.join(process.resourcesPath, 'python', 'backup_contents_reader.py')
        : path.join(__dirname, '../../python/backup_contents_reader.py');

      const pythonProcess = spawn('python3', [pythonScriptPath, args.backupPath]);

      let data = '';
      let error = '';

      pythonProcess.stdout.on('data', (chunk) => {
        data += chunk.toString();
      });

      pythonProcess.stderr.on('data', (chunk) => {
        error += chunk.toString();
      });

      pythonProcess.on('close', (code) => {
        if (code === 0) {
          try {
            const result = JSON.parse(data);
            resolve(result);
          } catch (e) {
            resolve({
              success: false,
              error: 'Failed to parse backup contents'
            });
          }
        } else {
          console.error('[IPC] Python script error:', error);
          resolve({
            success: false,
            error: error || 'Failed to read backup contents'
          });
        }
      });
    });
  });

  ipcMain.handle('extract-file', async (_, args: { backupPath: string, filePath: string }) => {
    console.log('[IPC] extract-file called:', args);

    return new Promise((resolve) => {
      const pythonScriptPath = app.isPackaged
        ? path.join(process.resourcesPath, 'python', 'backup_contents_reader.py')
        : path.join(__dirname, '../../python/backup_contents_reader.py');

      const pythonProcess = spawn('python3', [pythonScriptPath, args.backupPath, args.filePath]);

      let data = '';
      let error = '';

      pythonProcess.stdout.on('data', (chunk) => {
        data += chunk.toString();
      });

      pythonProcess.stderr.on('data', (chunk) => {
        error += chunk.toString();
      });

      pythonProcess.on('close', (code) => {
        if (code === 0) {
          try {
            const result = JSON.parse(data);
            if (result.success && result.path) {
              // Show the extracted file in Finder
              shell.showItemInFolder(result.path);
            }
            resolve(result);
          } catch (e) {
            resolve({
              success: false,
              error: 'Failed to extract file'
            });
          }
        } else {
          console.error('[IPC] Python script error:', error);
          resolve({
            success: false,
            error: error || 'Failed to extract file'
          });
        }
      });
    });
  });
}