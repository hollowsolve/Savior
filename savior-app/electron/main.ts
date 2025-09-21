import { app, BrowserWindow, Menu, Tray, ipcMain, shell, dialog } from 'electron';
import * as path from 'path';
import * as fs from 'fs';
import { spawn, ChildProcess } from 'child_process';
import { SaviorBridge } from './savior-bridge';
import { setupIpcHandlers } from './ipc/handlers';

let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;
let saviorBridge: SaviorBridge | null = null;
let isQuitting = false;

const isDev = process.env.NODE_ENV === 'development';
const isMac = process.platform === 'darwin';

function createWindow() {
  if (!app.isReady()) {
    console.error('Cannot create window before app is ready');
    app.whenReady().then(createWindow);
    return;
  }

  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    title: 'Savior',
    icon: path.join(__dirname, '../assets/icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    },
    titleBarStyle: isMac ? 'hiddenInset' : 'default',
    backgroundColor: '#0a0a0a',
    show: true  // Changed to true to show immediately
  });

  if (isDev) {
    // Load the built index.html from dist folder
    mainWindow.loadFile(path.join(__dirname, 'index.html'));
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, 'index.html'));
  }

  mainWindow.once('ready-to-show', () => {
    console.log('Window ready to show');
    mainWindow?.show();
    mainWindow?.focus();

    // Send current projects to the renderer when ready
    if (saviorBridge) {
      console.log('[DEBUG MAIN] Sending projects to renderer after ready-to-show');
      saviorBridge.getProjects().then(projects => {
        console.log('[DEBUG MAIN] Sending', projects.length, 'projects to renderer');
        mainWindow?.webContents.send('projects-updated', projects);
      });
    }
  });

  // Also handle page reload/navigation
  mainWindow.webContents.on('did-finish-load', () => {
    console.log('[DEBUG MAIN] Page finished loading/reloading');
    if (saviorBridge) {
      console.log('[DEBUG MAIN] Refreshing projects after page load');
      saviorBridge.getProjects().then(projects => {
        console.log('[DEBUG MAIN] Sending', projects.length, 'projects after reload');
        mainWindow?.webContents.send('projects-updated', projects);
      });
    }
  });

  // Fallback: show window after a delay if ready-to-show doesn't fire
  setTimeout(() => {
    if (mainWindow && !mainWindow.isVisible()) {
      console.log('Forcing window to show');
      mainWindow.show();
      mainWindow.focus();
    }
  }, 1000);

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Prevent app from quitting when window is closed (stay in tray)
  mainWindow.on('close', (event) => {
    if (!isQuitting && process.platform !== 'win32') {
      event.preventDefault();
      mainWindow?.hide();
    }
  });
}

function createTray() {
  if (!app.isReady()) {
    console.error('Cannot create tray before app is ready');
    return;
  }

  const iconPath = path.join(__dirname, '../assets/tray-icon.png');
  tray = new Tray(iconPath);

  updateTrayMenu([]);

  tray.on('click', () => {
    if (mainWindow) {
      mainWindow.isVisible() ? mainWindow.hide() : mainWindow.show();
    } else {
      createWindow();
    }
  });
}

function updateTrayMenu(projects: any[]) {
  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Open Savior',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
        } else {
          createWindow();
        }
      }
    },
    { type: 'separator' },
    {
      label: 'Projects',
      submenu: projects.length > 0 ? projects.map(project => ({
        label: `${project.name} ${project.active ? '🟢' : '⚪'}`,
        submenu: [
          {
            label: project.active ? 'Stop Watching' : 'Start Watching',
            click: () => {
              if (project.active) {
                saviorBridge?.stopProject(project.path);
              } else {
                saviorBridge?.watchProject(project.path);
              }
            }
          },
          {
            label: 'Force Backup',
            enabled: project.active,
            click: () => {
              saviorBridge?.saveBackup(
                project.path,
                'Manual backup from Savior app'
              );
            }
          },
          {
            label: 'Open in Finder',
            click: () => {
              shell.showItemInFolder(project.path);
            }
          }
        ]
      })) : [{ label: 'No projects', enabled: false }]
    },
    { type: 'separator' },
    {
      label: 'Add Project...',
      click: async () => {
        // Ensure app is ready before showing dialog
        if (!app.isReady()) {
          console.error('App not ready for dialog');
          return;
        }

        const result = await dialog.showOpenDialog({
          properties: ['openDirectory'],
          title: 'Select Project Directory'
        });

        if (!result.canceled && result.filePaths.length > 0) {
          saviorBridge?.watchProject(result.filePaths[0]);
        }
      }
    },
    { type: 'separator' },
    {
      label: 'Preferences',
      accelerator: 'CmdOrCtrl+,',
      click: () => {
        mainWindow?.webContents.send('open-settings');
      }
    },
    { type: 'separator' },
    {
      label: 'Quit Savior',
      accelerator: 'CmdOrCtrl+Q',
      click: () => {
        isQuitting = true;
        app.quit();
      }
    }
  ]);

  tray?.setContextMenu(contextMenu);
}

// App event handlers
app.whenReady().then(async () => {
  // Initialize Savior bridge
  saviorBridge = new SaviorBridge();

  // Set up IPC handlers
  setupIpcHandlers(saviorBridge);

  // Listen for project updates
  saviorBridge.on('projects-updated', (projects: any[]) => {
    console.log('[DEBUG MAIN] projects-updated event received');
    console.log('[DEBUG MAIN] Projects count:', projects.length);
    console.log('[DEBUG MAIN] Updating tray menu...');
    updateTrayMenu(projects);
    console.log('[DEBUG MAIN] Sending to renderer window...');
    mainWindow?.webContents.send('projects-updated', projects);
    console.log('[DEBUG MAIN] projects-updated sent to renderer');

    // Check if we have persistent projects and auto-launch is not enabled
    const hasPersistentProjects = projects.some(p => p.persistence === 'always');
    if (hasPersistentProjects) {
      // Check auto-launch status
      const { exec } = require('child_process');
      exec('savior autolaunch status', (error: any, stdout: string) => {
        if (!error && stdout.includes('disabled')) {
          console.log('[Main] Has persistent projects but auto-launch is disabled');
          // Optionally, you could prompt the user or enable it automatically
        }
      });
    }
  });

  saviorBridge.on('backup-started', (data: any) => {
    mainWindow?.webContents.send('backup-started', data);
  });

  saviorBridge.on('backup-completed', (data: any) => {
    mainWindow?.webContents.send('backup-completed', data);
  });

  saviorBridge.on('error', (error: any) => {
    mainWindow?.webContents.send('savior-error', error);
  });

  saviorBridge.on('file-changed', (data: any) => {
    console.log('[DEBUG MAIN] file-changed event:', data.projectPath, data.filePath);
    mainWindow?.webContents.send('file-changed', data);
  });

  createWindow();
  createTray();

  // Initial project load
  saviorBridge.getProjects();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    // Don't quit on Windows/Linux when window is closed
    // app.quit();
  }
});

app.on('activate', () => {
  // Ensure app is ready before creating window
  if (app.isReady()) {
    if (mainWindow === null) {
      createWindow();
    } else {
      mainWindow.show();
    }
  } else {
    // If app is not ready yet, wait for it
    app.whenReady().then(() => {
      if (mainWindow === null) {
        createWindow();
      }
    });
  }
});

app.on('before-quit', () => {
  isQuitting = true;
  saviorBridge?.shutdown();
});

