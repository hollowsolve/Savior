import { contextBridge, ipcRenderer } from 'electron';

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('saviorAPI', {
  // Projects
  getProjects: () => ipcRenderer.invoke('get-projects'),
  watchProject: (path: string, options: any) =>
    ipcRenderer.invoke('watch-project', path, options),
  removeAndWatch: (projectsToRemove: string[], newPath: string, options: any) =>
    ipcRenderer.invoke('remove-and-watch', projectsToRemove, newPath, options),
  stopProject: (path: string) => ipcRenderer.invoke('stop-project', path),
  addProject: (path: string) => ipcRenderer.invoke('add-project', path),
  removeProject: (path: string) => ipcRenderer.invoke('remove-project', path),

  // Backups
  getBackups: (projectPath: string) => ipcRenderer.invoke('get-backups', projectPath),
  saveBackup: (projectPath: string, description: string) =>
    ipcRenderer.invoke('save-backup', projectPath, description),
  restoreBackup: (projectPath: string, backupId: string, options: any) =>
    ipcRenderer.invoke('restore-backup', projectPath, backupId, options),
  compareBackups: (projectPath: string, backup1: string, backup2: string) =>
    ipcRenderer.invoke('compare-backups', projectPath, backup1, backup2),
  deleteBackup: (projectPath: string, backupId: string) =>
    ipcRenderer.invoke('delete-backup', projectPath, backupId),

  // Settings
  getSettings: () => ipcRenderer.invoke('get-settings'),
  updateSettings: (settings: any) => ipcRenderer.invoke('update-settings', settings),

  // Cloud
  getCloudStatus: () => ipcRenderer.invoke('get-cloud-status'),
  setupCloud: (config: any) => ipcRenderer.invoke('setup-cloud', config),
  syncCloud: (projectPath?: string) => ipcRenderer.invoke('sync-cloud', projectPath),

  // Daemon
  getDaemonStatus: () => ipcRenderer.invoke('get-daemon-status'),
  startDaemon: () => ipcRenderer.invoke('start-daemon'),
  stopDaemon: () => ipcRenderer.invoke('stop-daemon'),

  // File monitoring
  getModifiedFiles: (projectPath: string) => ipcRenderer.invoke('get-modified-files', projectPath),

  // System
  openInEditor: (path: string) => ipcRenderer.invoke('open-in-editor', path),
  showInFolder: (path: string) => ipcRenderer.invoke('show-in-folder', path),
  selectDirectory: () => ipcRenderer.invoke('select-directory'),

  // Backup Contents Viewer
  getBackupContents: (args: { backupPath: string }) => ipcRenderer.invoke('get-backup-contents', args),
  extractFile: (args: { backupPath: string, filePath: string }) => ipcRenderer.invoke('extract-file', args),

  // Events - Subscribe to events from main process
  on: (channel: string, callback: Function) => {
    const validChannels = [
      'projects-updated',
      'backup-started',
      'backup-completed',
      'backup-progress',
      'backup-error',
      'daemon-status',
      'cloud-sync-status',
      'python-error',
      'savior-error',
      'open-settings',
      'notification',
      'file-changed'
    ];

    if (validChannels.includes(channel)) {
      const subscription = (_: any, ...args: any[]) => callback(...args);
      ipcRenderer.on(channel, subscription);

      // Return unsubscribe function
      return () => {
        ipcRenderer.removeListener(channel, subscription);
      };
    }

    console.warn(`Invalid channel: ${channel}`);
    return () => {};
  },

  // Remove all listeners for a channel
  removeAllListeners: (channel: string) => {
    ipcRenderer.removeAllListeners(channel);
  }
});

// Type declarations for TypeScript
declare global {
  interface Window {
    saviorAPI: {
      // Projects
      getProjects: () => Promise<any[]>;
      watchProject: (path: string, options?: any) => Promise<any>;
      removeAndWatch: (projectsToRemove: string[], newPath: string, options?: any) => Promise<void>;
      stopProject: (path: string) => Promise<void>;
      addProject: (path: string) => Promise<void>;
      removeProject: (path: string) => Promise<void>;

      // Backups
      getBackups: (projectPath: string) => Promise<any[]>;
      saveBackup: (projectPath: string, description: string) => Promise<void>;
      restoreBackup: (projectPath: string, backupId: string, options?: any) => Promise<void>;
      compareBackups: (projectPath: string, backup1: string, backup2: string) => Promise<any>;
      deleteBackup: (projectPath: string, backupId: string) => Promise<void>;

      // Settings
      getSettings: () => Promise<any>;
      updateSettings: (settings: any) => Promise<void>;

      // Cloud
      getCloudStatus: () => Promise<any>;
      setupCloud: (config: any) => Promise<void>;
      syncCloud: (projectPath?: string) => Promise<void>;

      // Daemon
      getDaemonStatus: () => Promise<any>;
      startDaemon: () => Promise<void>;
      stopDaemon: () => Promise<void>;

      // File monitoring
      getModifiedFiles: (projectPath: string) => Promise<Array<{path: string, timestamp: Date}>>;

      // System
      openInEditor: (path: string) => Promise<void>;
      showInFolder: (path: string) => Promise<void>;
      selectDirectory: () => Promise<string | null>;

      // Events
      on: (channel: string, callback: Function) => () => void;
      removeAllListeners: (channel: string) => void;
    };
  }
}