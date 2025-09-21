import React from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import './styles/tailwind.css';

// Mock saviorAPI for browser environment
if (!window.saviorAPI) {
  window.saviorAPI = {
    // Projects
    getProjects: () => Promise.resolve([]),
    watchProject: () => Promise.resolve(),
    removeAndWatch: () => Promise.resolve(),
    stopProject: () => Promise.resolve(),
    addProject: () => Promise.resolve(),
    removeProject: () => Promise.resolve(),

    // Backups
    getBackups: () => Promise.resolve([]),
    saveBackup: () => Promise.resolve(),
    restoreBackup: () => Promise.resolve(),
    compareBackups: () => Promise.resolve({}),
    deleteBackup: () => Promise.resolve(),

    // Settings
    getSettings: () => Promise.resolve({ theme: 'dark', autoBackup: true }),
    updateSettings: () => Promise.resolve(),

    // Cloud
    getCloudStatus: () => Promise.resolve({}),
    setupCloud: () => Promise.resolve(),
    syncCloud: () => Promise.resolve(),

    // Daemon
    getDaemonStatus: () => Promise.resolve({}),
    startDaemon: () => Promise.resolve(),
    stopDaemon: () => Promise.resolve(),

    // File monitoring
    getModifiedFiles: () => Promise.resolve([]),

    // System
    openInEditor: () => Promise.resolve(),
    showInFolder: () => Promise.resolve(),
    selectDirectory: () => Promise.resolve('/example/path'),

    // Events
    on: () => () => {},
    removeAllListeners: () => {}
  };
}

const container = document.getElementById('root');
if (container) {
  const root = createRoot(container);
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
}