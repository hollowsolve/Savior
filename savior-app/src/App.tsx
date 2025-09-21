import React, { useState, useEffect, useRef } from 'react';
import './styles/app.css';
import BackupContentsViewer from './components/BackupContentsViewer';

interface BackupData {
  timestamp: string;
  fileCount: number;
  description?: string;
}

interface FileItem {
  path: string;
  status: 'normal' | 'modified' | 'stale';
  changes: { added: number; removed: number };
  size: string;
  timeAgo: string;
}

interface HistoryEntry {
  time: string;
  changes: string;
}

type ViewMode = 'projects' | 'details';

interface ProjectConfig {
  interval: number;
  smartMode: boolean;
  incremental: boolean;
  compression: number;
  excludeGit: boolean;
  persistence?: 'always' | 'session';
}

// Settings Form Component
const SettingsForm: React.FC<{
  initialConfig: ProjectConfig;
  onSave: (config: ProjectConfig) => void;
  onCancel: () => void;
  onStop: () => void;
}> = ({ initialConfig, onSave, onCancel, onStop }) => {
  const [config, setConfig] = useState(initialConfig);

  const handleSave = () => {
    onSave(config);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Backup Interval */}
      <div>
        <label style={{
          display: 'block',
          marginBottom: '0.5rem',
          fontSize: '0.875rem',
          fontWeight: 500,
          color: 'var(--text)'
        }}>
          Backup Interval
        </label>
        <div style={{ position: 'relative' }}>
          <input
            type="number"
            min="1"
            max="1440"
            value={config.interval}
            onChange={(e) => setConfig(prev => ({ ...prev, interval: parseInt(e.target.value) || 20 }))}
            style={{
              width: '100%',
              padding: '0.75rem 3rem 0.75rem 1rem',
              background: 'var(--input-bg)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              color: 'var(--text)',
              fontSize: '0.9375rem',
              transition: 'border-color 0.2s'
            }}
            onFocus={(e) => e.currentTarget.style.borderColor = 'var(--accent)'}
            onBlur={(e) => e.currentTarget.style.borderColor = 'var(--border)'}
          />
          <span style={{
            position: 'absolute',
            right: '1rem',
            top: '50%',
            transform: 'translateY(-50%)',
            color: 'var(--text-dim)',
            fontSize: '0.875rem',
            pointerEvents: 'none'
          }}>
            minutes
          </span>
        </div>
        <p style={{
          fontSize: '0.75rem',
          color: 'var(--text-dim)',
          marginTop: '0.5rem',
          margin: '0.5rem 0 0 0'
        }}>
          How often to create automatic backups (1-1440 minutes)
        </p>
      </div>

      {/* Compression Level */}
      <div>
        <label style={{
          display: 'block',
          marginBottom: '0.5rem',
          fontSize: '0.875rem',
          fontWeight: 500,
          color: 'var(--text)'
        }}>
          Compression Level
        </label>
        <div style={{
          background: 'var(--input-bg)',
          borderRadius: '8px',
          padding: '1rem',
          border: '1px solid var(--border)'
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '1rem',
            marginBottom: '0.75rem'
          }}>
            <span style={{
              fontSize: '0.75rem',
              color: 'var(--text-dim)',
              minWidth: '30px'
            }}>
              0
            </span>
            <input
              type="range"
              min="0"
              max="9"
              value={config.compression}
              onChange={(e) => setConfig(prev => ({ ...prev, compression: parseInt(e.target.value) }))}
              style={{
                flex: 1,
                height: '4px',
                background: 'var(--surface)',
                borderRadius: '2px',
                outline: 'none',
                WebkitAppearance: 'none' as any
              }}
            />
            <span style={{
              fontSize: '0.75rem',
              color: 'var(--text-dim)',
              minWidth: '30px',
              textAlign: 'right'
            }}>
              9
            </span>
          </div>
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            gap: '0.5rem',
            marginBottom: '0.75rem'
          }}>
            <div style={{
              width: '48px',
              height: '48px',
              borderRadius: '12px',
              background: 'var(--accent)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.5rem',
              fontWeight: 700,
              color: 'white'
            }}>
              {config.compression}
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{
                fontSize: '0.875rem',
                fontWeight: 500,
                color: 'var(--text)'
              }}>
                {config.compression === 0 ? 'No Compression' :
                 config.compression <= 3 ? 'Fast' :
                 config.compression <= 6 ? 'Balanced' : 'Maximum'}
              </div>
              <div style={{
                fontSize: '0.75rem',
                color: 'var(--text-dim)'
              }}>
                {config.compression === 0 ? 'Fastest, most space' :
                 config.compression <= 3 ? 'Good for large files' :
                 config.compression <= 6 ? 'Recommended' : 'Slowest, least space'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Backup Options */}
      <div>
        <label style={{
          display: 'block',
          marginBottom: '0.75rem',
          fontSize: '0.875rem',
          fontWeight: 500,
          color: 'var(--text)'
        }}>
          Backup Options
        </label>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <label style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: '0.75rem',
            padding: '1rem',
            background: 'var(--surface)',
            borderRadius: '8px',
            cursor: 'pointer',
            transition: 'background 0.2s',
            border: '1px solid var(--border)'
          }}>
            <input
              type="checkbox"
              checked={config.smartMode}
              onChange={(e) => setConfig(prev => ({ ...prev, smartMode: e.target.checked }))}
              style={{
                marginTop: '2px',
                width: '16px',
                height: '16px',
                cursor: 'pointer'
              }}
            />
            <div style={{ flex: 1 }}>
              <div style={{
                fontSize: '0.9375rem',
                fontWeight: 500,
                color: 'var(--text)',
                marginBottom: '0.25rem'
              }}>
                Smart Mode
              </div>
              <div style={{
                fontSize: '0.8125rem',
                color: 'var(--text-dim)',
                lineHeight: 1.4
              }}>
                Only backup after actual file changes, ignoring pure save events
              </div>
            </div>
          </label>

          <label style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: '0.75rem',
            padding: '1rem',
            background: 'var(--surface)',
            borderRadius: '8px',
            cursor: 'pointer',
            transition: 'background 0.2s',
            border: '1px solid var(--border)'
          }}>
            <input
              type="checkbox"
              checked={config.incremental}
              onChange={(e) => setConfig(prev => ({ ...prev, incremental: e.target.checked }))}
              style={{
                marginTop: '2px',
                width: '16px',
                height: '16px',
                cursor: 'pointer'
              }}
            />
            <div style={{ flex: 1 }}>
              <div style={{
                fontSize: '0.9375rem',
                fontWeight: 500,
                color: 'var(--text)',
                marginBottom: '0.25rem'
              }}>
                Incremental Backups
              </div>
              <div style={{
                fontSize: '0.8125rem',
                color: 'var(--text-dim)',
                lineHeight: 1.4
              }}>
                Only save changes since last backup, saving space and time
              </div>
            </div>
          </label>

          <label style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: '0.75rem',
            padding: '1rem',
            background: 'var(--surface)',
            borderRadius: '8px',
            cursor: 'pointer',
            transition: 'background 0.2s',
            border: '1px solid var(--border)'
          }}>
            <input
              type="checkbox"
              checked={config.excludeGit}
              onChange={(e) => setConfig(prev => ({ ...prev, excludeGit: e.target.checked }))}
              style={{
                marginTop: '2px',
                width: '16px',
                height: '16px',
                cursor: 'pointer'
              }}
            />
            <div style={{ flex: 1 }}>
              <div style={{
                fontSize: '0.9375rem',
                fontWeight: 500,
                color: 'var(--text)',
                marginBottom: '0.25rem'
              }}>
                Exclude .git Directory
              </div>
              <div style={{
                fontSize: '0.8125rem',
                color: 'var(--text-dim)',
                lineHeight: 1.4
              }}>
                Don't backup git repository data, saving significant space
              </div>
            </div>
          </label>
        </div>
      </div>

      {/* Actions */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem',
        marginTop: '1rem',
        paddingTop: '1.5rem',
        borderTop: '1px solid var(--border)'
      }}>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button
            onClick={onCancel}
            style={{
              flex: 1,
              padding: '0.875rem',
              background: 'transparent',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              color: 'var(--text-dim)',
              cursor: 'pointer',
              fontSize: '0.9375rem',
              fontWeight: 500,
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'var(--accent)';
              e.currentTarget.style.color = 'var(--accent)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--border)';
              e.currentTarget.style.color = 'var(--text-dim)';
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            style={{
              flex: 1.5,
              padding: '0.875rem',
              background: 'var(--accent)',
              border: 'none',
              borderRadius: '8px',
              color: 'white',
              cursor: 'pointer',
              fontSize: '0.9375rem',
              fontWeight: 600,
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => e.currentTarget.style.opacity = '0.9'}
            onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
          >
            Save Settings
          </button>
        </div>

        {/* Stop Watching Button */}
        <button
          onClick={onStop}
          style={{
            width: '100%',
            padding: '0.875rem',
            background: 'transparent',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '8px',
            color: 'rgba(239, 68, 68, 0.9)',
            cursor: 'pointer',
            fontSize: '0.9375rem',
            fontWeight: 500,
            transition: 'all 0.2s',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.5rem'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.5)';
            e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.3)';
            e.currentTarget.style.background = 'transparent';
          }}
        >
          <svg width="20" height="20" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-2 0v6a1 1 0 102 0V7zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V7a1 1 0 00-1-1z" clipRule="evenodd"/>
          </svg>
          Stop Watching This Project
        </button>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  // State
  const [viewMode, setViewMode] = useState<ViewMode>('projects');
  const [projects, setProjects] = useState<any[]>([]);
  const [selectedProject, setSelectedProject] = useState<any>(null);
  const [projectCountdowns, setProjectCountdowns] = useState<Record<string, number>>({});
  const [showConfigDialog, setShowConfigDialog] = useState(false);
  const [pendingProjectPath, setPendingProjectPath] = useState<string | null>(null);
  const [showOverlapDialog, setShowOverlapDialog] = useState(false);
  const [overlapInfo, setOverlapInfo] = useState<{
    overlaps: any[];
    newPath: string;
    newName: string;
  } | null>(null);
  const [showProjectSettings, setShowProjectSettings] = useState(false);
  const [settingsProject, setSettingsProject] = useState<any>(null);
  const [showStopConfirm, setShowStopConfirm] = useState(false);
  const [showBackupContents, setShowBackupContents] = useState(false);
  const [selectedBackupPath, setSelectedBackupPath] = useState<string | null>(null);
  const [projectConfig, setProjectConfig] = useState<ProjectConfig>({
    interval: 20,
    smartMode: true,
    incremental: true,
    compression: 6,
    excludeGit: false,
    persistence: 'always'
  });
  const [timeRange, setTimeRange] = useState<'1h' | '6h' | '24h' | '7d'>('1h');
  const [fileView, setFileView] = useState<'recent' | 'modified' | 'all'>('recent');
  const [countdown, setCountdown] = useState(0); // Start at 0, only start when folder linked
  const [isWatching, setIsWatching] = useState(false); // Track if we're watching a folder
  const [searchQuery, setSearchQuery] = useState('');
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [selectedFile, setSelectedFile] = useState<string>('');
  const [notification, setNotification] = useState<{ show: boolean; message: string; type: 'success' | 'error' | 'info' }>({
    show: false,
    message: '',
    type: 'success'
  });
  const [backupIndicatorActive, setBackupIndicatorActive] = useState(false);

  // Graph data - start with flat line at 0
  const [graphData, setGraphData] = useState<number[]>(
    Array.from({ length: 11 }, () => 0)
  );

  // Stats - all starting at 0
  const [stats, setStats] = useState({
    projectCount: 0,
    fileCount: 0,
    protectedCount: 0,
    modifiedCount: 0,
    staleCount: 0,
    totalSize: '0 MB',
    recoveriesCount: 0,
    storagePercent: 0,
    peakTime: '--:--'
  });

  // Files data - start empty
  const [modifiedFiles, setModifiedFiles] = useState<Record<string, FileItem[]>>({});
  const [files, setFiles] = useState<FileItem[]>([]);

  // Countdown effect for individual projects
  useEffect(() => {
    if (!projects || projects.length === 0) {
      setProjectCountdowns({});
      return;
    }

    // Initialize countdowns for new projects
    const newCountdowns = { ...projectCountdowns };
    projects.forEach(project => {
      if (project.active && !newCountdowns[project.path]) {
        // Calculate countdown from next backup time if available
        if (project.nextBackup) {
          const nextBackupTime = new Date(project.nextBackup);
          const now = new Date();
          const secondsUntilBackup = Math.max(0, Math.floor((nextBackupTime.getTime() - now.getTime()) / 1000));
          newCountdowns[project.path] = secondsUntilBackup;
          console.log('[DEBUG] Initialized countdown for', project.path);
          console.log('[DEBUG]   Next backup:', project.nextBackup);
          console.log('[DEBUG]   Seconds until:', secondsUntilBackup);
        } else {
          // Default to watch interval or 20 minutes for new projects
          const interval = project.watchInterval || 20;
          newCountdowns[project.path] = interval * 60;
          console.log('[DEBUG] No nextBackup, using default interval for', project.path);
        }
      } else if (!project.active && newCountdowns[project.path]) {
        // Remove countdown for stopped projects
        delete newCountdowns[project.path];
      } else if (project.active && project.nextBackup && newCountdowns[project.path] !== undefined) {
        // Always sync with the actual next backup time on reload
        const nextBackupTime = new Date(project.nextBackup);
        const now = new Date();
        const secondsUntilBackup = Math.max(0, Math.floor((nextBackupTime.getTime() - now.getTime()) / 1000));

        // Update the countdown to match the actual time
        newCountdowns[project.path] = secondsUntilBackup;
        console.log('[DEBUG] Synced existing countdown for', project.path);
        console.log('[DEBUG]   Next backup:', project.nextBackup);
        console.log('[DEBUG]   Updated seconds:', secondsUntilBackup);
      }
    });

    // Only update if there are changes
    if (Object.keys(newCountdowns).length !== Object.keys(projectCountdowns).length) {
      setProjectCountdowns(newCountdowns);
    }

    // Set up interval to update all countdowns
    const timer = setInterval(() => {
      setProjectCountdowns((prev) => {
        const updated = { ...prev };
        let hasChanges = false;

        Object.keys(updated).forEach(path => {
          if (updated[path] > 0) {
            updated[path]--;
            hasChanges = true;

            // Reset countdown when it reaches 0
            if (updated[path] === 0) {
              // Find the project to get its interval
              const project = projects.find(p => p.path === path);
              const interval = project?.watchInterval || 20;
              updated[path] = interval * 60;
              // Could trigger a backup here if needed
              flashBackup();
            }
          }
        });

        return hasChanges ? updated : prev;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [projects]);

  // Countdown effect for details view - only runs when viewing a specific project
  useEffect(() => {
    if (!isWatching || viewMode !== 'details' || !selectedProject) {
      setCountdown(0);
      return;
    }

    // Use the project-specific countdown
    const projectCountdown = projectCountdowns[selectedProject.path];
    if (projectCountdown !== undefined) {
      setCountdown(projectCountdown);
    }
  }, [isWatching, viewMode, selectedProject, projectCountdowns]);

  // Update peak time every minute
  useEffect(() => {
    const timer = setInterval(() => {
      setStats(prev => ({
        ...prev,
        peakTime: new Date().toLocaleTimeString('en-US', {
          hour: 'numeric',
          minute: '2-digit',
          hour12: true
        })
      }));
    }, 60000);

    return () => clearInterval(timer);
  }, []);

  // Listen for Electron IPC events
  useEffect(() => {
    console.log('[DEBUG] App mounted, checking saviorAPI...');
    if (!(window as any).saviorAPI) {
      console.error('[DEBUG] saviorAPI not available on mount!');
      return;
    }
    console.log('[DEBUG] saviorAPI is available');

    const handleProjectsUpdated = (projectsList: any[]) => {
      setProjects(projectsList);
      if (projectsList && projectsList.length > 0) {
        setIsWatching(true);
        setStats(prev => ({
          ...prev,
          projectCount: projectsList.length,
          fileCount: projectsList.reduce((sum, p) => sum + (p.fileCount || 0), 0)
        }));
        // If we have a selected project, update it
        if (selectedProject) {
          const updated = projectsList.find(p => p.path === selectedProject.path);
          if (updated) setSelectedProject(updated);
        }
      } else {
        setIsWatching(false);
      }
    };

    const handleBackupStarted = () => {
      showNotification('Backup started...');
      setBackupIndicatorActive(true);
    };

    const handleBackupCompleted = (data: any) => {
      showNotification('Backup completed successfully!');
      setBackupIndicatorActive(false);
      updateGraph();
      updateStats();

      // Reset countdown for the project that just backed up
      if (data && data.path) {
        const project = projects.find(p => p.path === data.path);
        const interval = project?.watchInterval || 20;
        setProjectCountdowns(prev => ({
          ...prev,
          [data.path]: interval * 60
        }));
      }
    };

    const handleError = (error: any) => {
      showNotification(`Error: ${error.message || 'Unknown error'}`);
    };

    const handleFileChanged = (data: any) => {
      console.log('[DEBUG] File changed event:', data);

      // Update modified files for the project
      setModifiedFiles(prev => ({
        ...prev,
        [data.projectPath]: data.allModifiedFiles.map((file: any) => ({
          path: file.path,
          status: 'modified' as const,
          changes: { added: 0, removed: 0 },
          size: '--',
          timeAgo: formatTimeAgo(new Date(file.timestamp))
        }))
      }));

      // Update files list if viewing this project
      if (selectedProject?.path === data.projectPath || viewMode === 'projects') {
        const projectFiles = data.allModifiedFiles.map((file: any) => ({
          path: file.path,
          status: 'modified' as const,
          changes: { added: 0, removed: 0 },
          size: '--',
          timeAgo: formatTimeAgo(new Date(file.timestamp))
        }));
        setFiles(projectFiles);
      }

      // Update modified count in stats
      setStats(prev => ({
        ...prev,
        modifiedCount: data.allModifiedFiles.length
      }));
    };

    // Register event listeners
    const unsubscribe1 = (window as any).saviorAPI?.on('projects-updated', handleProjectsUpdated);
    const unsubscribe2 = (window as any).saviorAPI?.on('backup-started', handleBackupStarted);
    const unsubscribe3 = (window as any).saviorAPI?.on('backup-completed', handleBackupCompleted);
    const unsubscribe4 = (window as any).saviorAPI?.on('savior-error', handleError);
    const unsubscribe5 = (window as any).saviorAPI?.on('file-changed', handleFileChanged);

    // Initial load
    (window as any).saviorAPI?.getProjects().then((projects: any[]) => {
      handleProjectsUpdated(projects);
    }).catch(() => {
      console.log('No projects currently being watched');
    });

    // Refresh projects on focus/visibility change
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        console.log('[DEBUG] App became visible, refreshing projects...');
        (window as any).saviorAPI?.getProjects().then((projects: any[]) => {
          console.log('[DEBUG] Refreshed projects:', projects.length);
          handleProjectsUpdated(projects);
        }).catch((err: any) => {
          console.log('[DEBUG] Error refreshing projects:', err);
        });
      }
    };

    const handleFocus = () => {
      console.log('[DEBUG] Window focused, refreshing projects...');
      (window as any).saviorAPI?.getProjects().then((projects: any[]) => {
        console.log('[DEBUG] Refreshed projects on focus:', projects.length);
        handleProjectsUpdated(projects);
      }).catch((err: any) => {
        console.log('[DEBUG] Error refreshing projects on focus:', err);
      });
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('focus', handleFocus);

    // Cleanup
    return () => {
      unsubscribe1?.();
      unsubscribe2?.();
      unsubscribe3?.();
      unsubscribe4?.();
      unsubscribe5?.();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('focus', handleFocus);
    };
  }, []);

  // Helper functions
  const formatTimeAgo = (date: Date): string => {
    const now = new Date();
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  };

  // Functions
  const flashBackup = () => {
    setBackupIndicatorActive(true);
    showNotification('Backup completed successfully!');
    updateGraph();
    updateStats();

    setTimeout(() => {
      setBackupIndicatorActive(false);
    }, 500);
  };

  const updateGraph = () => {
    setGraphData(prev => {
      const newData = [...prev.slice(1), Math.max(20, Math.random() * 80)];
      return newData;
    });
  };

  const updateStats = () => {
    setStats(prev => ({
      ...prev,
      protectedCount: prev.protectedCount + Math.floor(Math.random() * 3),
      recoveriesCount: Math.random() > 0.9 ? prev.recoveriesCount + 1 : prev.recoveriesCount
    }));
  };

  const showNotification = (message: string, type: 'success' | 'error' | 'info' = 'success') => {
    console.log(`[NOTIFICATION ${type.toUpperCase()}]`, message);
    setNotification({ show: true, message, type });
    setTimeout(() => {
      setNotification({ show: false, message: '', type: 'success' });
    }, type === 'error' ? 5000 : 3000); // Errors stay longer
  };

  const [currentProject, setCurrentProject] = useState<string | null>(null);

  const forceBackup = async () => {
    // Get the currently selected project or first project if in projects view
    const projectToBackup = selectedProject || (projects && projects.length > 0 ? projects[0] : null);

    if (!isWatching || !projectToBackup) {
      showNotification('No folder is being watched', 'error');
      return;
    }

    try {
      console.log('[DEBUG] Forcing backup for:', projectToBackup.path);
      showNotification('Creating backup...', 'info');

      // Call the Electron IPC to force a backup
      await (window as any).saviorAPI.saveBackup(projectToBackup.path, 'Manual backup');

      showNotification('Backup completed successfully!', 'success');
      flashBackup();

      // Reset countdown for this project
      setProjectCountdowns(prev => ({
        ...prev,
        [projectToBackup.path]: (projectToBackup.watchInterval || 20) * 60
      }));
    } catch (error) {
      console.error('[DEBUG] Backup failed:', error);
      showNotification('Failed to create backup', 'error');
    }
  };

  const linkFolder = async () => {
    console.log('[DEBUG] Starting linkFolder process');
    try {
      // Check if saviorAPI exists
      if (!(window as any).saviorAPI) {
        console.error('[DEBUG] saviorAPI not available!');
        showNotification('Error: Electron API not available', 'error');
        return;
      }

      console.log('[DEBUG] Calling selectDirectory...');
      // Call Electron IPC to open folder dialog
      const folderPath = await (window as any).saviorAPI.selectDirectory();
      console.log('[DEBUG] selectDirectory returned:', folderPath);

      if (folderPath) {
        // Show configuration dialog
        console.log('[DEBUG] Setting pendingProjectPath to:', folderPath);
        setPendingProjectPath(folderPath);

        console.log('[DEBUG] Setting showConfigDialog to true');
        setShowConfigDialog(true);

        console.log('[DEBUG] Configuration dialog should now be visible');
        console.log('[DEBUG] Current state - showConfigDialog:', true, 'pendingProjectPath:', folderPath);
      } else {
        console.log('[DEBUG] No folder selected (user cancelled)');
        showNotification('No folder selected', 'info');
      }
    } catch (error: any) {
      console.error('[DEBUG] Error in linkFolder:', error);
      console.error('[DEBUG] Error stack:', error?.stack);
      showNotification(`Error: ${error?.message || 'Failed to select folder'}`, 'error');
    }
  };

  const handleConfigSubmit = async () => {
    if (!pendingProjectPath) {
      console.log('[DEBUG] No pending project path');
      return;
    }

    console.log('[DEBUG] Submitting config for:', pendingProjectPath);
    console.log('[DEBUG] Config options:', projectConfig);

    try {
      // Start watching with configuration
      const result = await (window as any).saviorAPI.watchProject(pendingProjectPath, projectConfig);
      console.log('[DEBUG] Watch result:', result);

      // Check if there's an overlap error
      if (result?.error === 'PROJECT_OVERLAP') {
        console.log('[DEBUG] Project overlap detected:', result.overlaps);
        setOverlapInfo({
          overlaps: result.overlaps,
          newPath: result.newPath,
          newName: result.newPath.split('/').pop() || 'folder'
        });
        setShowOverlapDialog(true);
        // Keep config dialog open but hide it temporarily
        setShowConfigDialog(false);
        return;
      }

      setIsWatching(true);
      setCurrentProject(pendingProjectPath);
      setStats(prev => ({ ...prev, projectCount: prev.projectCount + 1 }));
      showNotification(`Now watching: ${pendingProjectPath.split('/').pop()}`, 'success');
      setShowConfigDialog(false);
      setPendingProjectPath(null);
      console.log('[DEBUG] Successfully started watching project');
    } catch (error: any) {
      console.error('[DEBUG] Error starting watch:', error);
      const errorMessage = error?.message || error?.toString() || 'Failed to start watching project';
      showNotification(errorMessage, 'error');
      // Don't close dialog on error so user can try again
    }
  };

  const handleFileClick = (filePath: string) => {
    setSelectedFile(filePath);
    setShowHistoryModal(true);
  };

  const handleProjectSelect = (project: any) => {
    setSelectedProject(project);
    setCurrentProject(project.path);
    setViewMode('details');
  };

  const handleBackToProjects = () => {
    setViewMode('projects');
    setSelectedProject(null);
  };

  const handleProjectSettings = (project: any, e?: React.MouseEvent) => {
    if (e) {
      e.stopPropagation(); // Prevent project card click
    }
    setSettingsProject(project);
    setShowProjectSettings(true);
  };

  const handleSaveProjectSettings = async (updatedConfig: ProjectConfig) => {
    if (!settingsProject) return;

    try {
      // Stop the current project
      await (window as any).saviorAPI.stopProject(settingsProject.path);

      // Wait a moment
      await new Promise(resolve => setTimeout(resolve, 500));

      // Start with new settings
      await (window as any).saviorAPI.watchProject(settingsProject.path, updatedConfig);

      showNotification(`Updated settings for ${settingsProject.name}`, 'success');
      setShowProjectSettings(false);

      // Refresh project list
      const projects = await (window as any).saviorAPI.getProjects();
      setProjects(projects);
    } catch (error: any) {
      console.error('Error updating project settings:', error);
      showNotification('Failed to update project settings', 'error');
    }
  };

  const handleStopWatching = async () => {
    if (!settingsProject) return;

    setShowStopConfirm(false);
    setShowProjectSettings(false);

    try {
      await (window as any).saviorAPI.stopProject(settingsProject.path);
      showNotification(`Stopped watching ${settingsProject.name}`, 'success');

      // Refresh project list
      const projects = await (window as any).saviorAPI.getProjects();
      setProjects(projects);

      // If we were viewing this project's details, go back to projects view
      if (selectedProject?.path === settingsProject.path) {
        setViewMode('projects');
        setSelectedProject(null);
      }
    } catch (error: any) {
      console.error('Error stopping project:', error);
      showNotification('Failed to stop watching project', 'error');
    }
  };

  const generateHistory = (): HistoryEntry[] => {
    const history: HistoryEntry[] = [];
    const now = new Date();

    for (let i = 0; i < 8; i++) {
      const time = new Date(now.getTime() - i * 3600000);
      history.push({
        time: time.toLocaleString('en-US', {
          month: 'short',
          day: 'numeric',
          hour: 'numeric',
          minute: '2-digit'
        }),
        changes: `+${Math.floor(Math.random() * 100)} -${Math.floor(Math.random() * 50)} lines`
      });
    }

    return history;
  };

  const getTimeLabels = () => {
    switch(timeRange) {
      case '1h':
        return ['-60m', '-45m', '-30m', '-15m', 'now'];
      case '6h':
        return ['-6h', '-4.5h', '-3h', '-1.5h', 'now'];
      case '24h':
        return ['-24h', '-18h', '-12h', '-6h', 'now'];
      case '7d':
        return ['-7d', '-5d', '-3d', '-1d', 'now'];
      default:
        return ['-60m', '-45m', '-30m', '-15m', 'now'];
    }
  };

  const filteredFiles = files.filter(file => {
    // Filter by search
    if (searchQuery && !file.path.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }

    // Filter by view
    if (fileView === 'modified') {
      return file.status === 'modified' || file.status === 'stale';
    }

    return true;
  });

  // Generate graph path
  const generateGraphPath = (data: number[], width: number, height: number) => {
    return data.map((value, index) => {
      const x = (index / (data.length - 1)) * width;
      const y = height - value;
      return `${index === 0 ? 'M' : 'L'} ${x} ${y}`;
    }).join(' ');
  };

  const graphLinePath = generateGraphPath(graphData, 400, 120);
  const graphFillPath = `${graphLinePath} L 400 120 L 0 120 Z`;

  return (
    <div className="container">
      {/* Header */}
      <header className="header">
        <div className="logo-group" onClick={handleBackToProjects} style={{ cursor: 'pointer' }}>
          <svg className="logo" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
            <g opacity="0.9">
              <path d="M 50 15 A 35 35 0 0 1 80 35 L 65 42 A 20 20 0 0 0 50 30 Z" fill="#4ade80"/>
              <path d="M 20 35 A 35 35 0 0 1 50 15 L 50 30 A 20 20 0 0 0 35 42 Z" fill="#d4d4d4"/>
              <path d="M 80 65 A 35 35 0 0 1 50 85 L 50 70 A 20 20 0 0 0 65 58 Z" fill="#4ade80"/>
              <path d="M 50 85 A 35 35 0 0 1 20 65 L 35 58 A 20 20 0 0 0 50 70 Z" fill="#d4d4d4"/>
              <path d="M 80 35 A 35 35 0 0 1 80 65 L 65 58 A 20 20 0 0 0 65 42 Z" fill="#d4d4d4"/>
              <path d="M 20 65 A 35 35 0 0 1 20 35 L 35 42 A 20 20 0 0 0 35 58 Z" fill="#4ade80"/>
            </g>
          </svg>
          <h1 className="wordmark">Savior</h1>
        </div>

        <div className="status-info" onClick={handleBackToProjects} style={{ cursor: 'pointer' }}>
          <div className="status-item">
            <span className="status-dot"></span>
            <span>Active</span>
          </div>
          <div className="status-item">
            <span>{stats.projectCount}</span>
            <span>projects</span>
          </div>
          <div className="status-item">
            <span>{stats.fileCount.toLocaleString()}</span>
            <span>files</span>
          </div>
        </div>
      </header>

      {/* Projects Overview */}
      {viewMode === 'projects' && (
        <div className="projects-overview">
          <div className="projects-header">
            <h2 className="projects-title">Your Projects</h2>
            <button className="action-btn" onClick={linkFolder} style={{ width: 'auto', padding: '0.75rem 1.5rem' }}>
              <svg className="action-icon" fill="currentColor" viewBox="0 0 20 20">
                <path d="M8 2a1 1 0 011 1v1h2V3a1 1 0 112 0v1h2a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2V6a2 2 0 012-2h2V3a1 1 0 011-1z"/>
              </svg>
              Add Project
            </button>
            {/* Debug info */}
            <span style={{ fontSize: '10px', color: 'red', marginLeft: '10px' }}>
              Dialog: {showConfigDialog ? 'OPEN' : 'CLOSED'} | Path: {pendingProjectPath || 'NONE'}
            </span>
          </div>

          <div className="projects-grid">
            {projects.length === 0 ? (
              <div className="empty-projects">
                <svg width="64" height="64" fill="currentColor" viewBox="0 0 20 20" style={{ opacity: 0.2, margin: '0 auto 1.5rem' }}>
                  <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"/>
                </svg>
                <h3 style={{ fontSize: '1.25rem', marginBottom: '0.5rem', color: 'var(--text-bright)' }}>
                  No Projects Being Watched
                </h3>
                <p style={{ color: 'var(--text-dim)', marginBottom: '1.5rem' }}>
                  Add a project to start automatic backups
                </p>
                <button className="action-btn" onClick={linkFolder} style={{ display: 'inline-flex', width: 'auto', padding: '0.75rem 2rem' }}>
                  <svg className="action-icon" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M8 2a1 1 0 011 1v1h2V3a1 1 0 112 0v1h2a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2V6a2 2 0 012-2h2V3a1 1 0 011-1z"/>
                  </svg>
                  Link Your First Project
                </button>
              </div>
            ) : (
              projects.map((project) => (
                <div key={project.id} className="project-card" onClick={() => handleProjectSelect(project)}>
                  <div className="project-card-header">
                    <div className="project-icon">
                      <svg fill="currentColor" viewBox="0 0 20 20">
                        <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"/>
                      </svg>
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <div className="project-status-badge">{project.mode || 'smart, incremental'}</div>
                      {project.persistence === 'session' && (
                        <div className="project-status-badge" style={{
                          background: 'rgba(251, 191, 36, 0.1)',
                          color: 'rgba(251, 191, 36, 0.9)',
                          border: '1px solid rgba(251, 191, 36, 0.3)'
                        }}>
                          Session Only
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="project-card-body">
                    <h3 className="project-name">{project.name}</h3>
                    <p className="project-path">{project.path}</p>

                    {/* Countdown Timer */}
                    <div style={{
                      padding: '0.75rem 0',
                      borderTop: '1px solid var(--border)',
                      borderBottom: '1px solid var(--border)',
                      margin: '1rem 0',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      fontSize: '0.875rem'
                    }}>
                      <svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20" style={{ opacity: 0.6 }}>
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd"/>
                      </svg>
                      <span style={{ color: 'var(--text-dim)' }}>Next backup in</span>
                      <span style={{
                        color: 'var(--accent)',
                        fontWeight: 600,
                        fontFamily: 'var(--mono)'
                      }}>
                        {projectCountdowns[project.path] && projectCountdowns[project.path] > 0
                          ? `${Math.floor(projectCountdowns[project.path] / 60)}m ${projectCountdowns[project.path] % 60}s`
                          : 'Starting...'}
                      </span>
                    </div>

                    <div className="project-stats">
                      <div className="project-stat">
                        <span className="stat-label">Files</span>
                        <span className="stat-value">{project.fileCount || 0}</span>
                      </div>
                      <div className="project-stat">
                        <span className="stat-label">Status</span>
                        <span className="stat-value" style={{ color: 'var(--accent)' }}>Active</span>
                      </div>
                    </div>
                  </div>
                  <div className="project-card-footer">
                    <button className="project-action" onClick={(e) => handleProjectSettings(project, e)}>
                      <svg fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd"/>
                      </svg>
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Project Details View */}
      {viewMode === 'details' && selectedProject && (
        <>
          {/* Breadcrumb Navigation */}
          <div style={{
            marginBottom: '1rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.9rem'
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              <button
                onClick={handleBackToProjects}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-dim)',
                  cursor: 'pointer',
                  padding: 0,
                  font: 'inherit',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                  transition: 'color 0.2s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent)'}
                onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-dim)'}
              >
                <svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clipRule="evenodd"/>
                </svg>
                Projects
              </button>
              <span style={{ color: 'var(--text-dim)' }}>/</span>
              <span style={{ color: 'var(--text-bright)', fontWeight: 500 }}>
                {selectedProject.name}
              </span>
              {selectedProject.persistence === 'session' && (
                <>
                  <span style={{ color: 'var(--text-dim)' }}>/</span>
                  <span style={{
                    fontSize: '0.8rem',
                    padding: '0.125rem 0.5rem',
                    background: 'rgba(251, 191, 36, 0.1)',
                    color: 'rgba(251, 191, 36, 0.9)',
                    border: '1px solid rgba(251, 191, 36, 0.3)',
                    borderRadius: '4px'
                  }}>
                    Session Only
                  </span>
                </>
              )}
            </div>

            {/* Backup Actions */}
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              {/* Contents Button */}
              <button
                onClick={() => {
                  // Get the most recent backup for this project
                  const backupPath = `${selectedProject.path}/.savior`;
                  setSelectedBackupPath(backupPath);
                  setShowBackupContents(true);
                }}
                style={{
                  background: 'var(--surface)',
                  border: '1px solid var(--border)',
                  color: 'var(--text)',
                  cursor: 'pointer',
                  padding: '0.5rem 0.75rem',
                  borderRadius: '6px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  fontSize: '0.875rem',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'var(--accent)';
                  e.currentTarget.style.borderColor = 'var(--accent)';
                  e.currentTarget.style.color = 'white';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'var(--surface)';
                  e.currentTarget.style.borderColor = 'var(--border)';
                  e.currentTarget.style.color = 'var(--text)';
                }}
              >
                <svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd"/>
                </svg>
                Contents
              </button>

              {/* Open Backup Folder Button */}
              <button
                onClick={() => {
                  const backupPath = `${selectedProject.path}/.savior`;
                  (window as any).saviorAPI.showInFolder(backupPath);
                  showNotification('Opening backup folder in Finder');
                }}
                style={{
                  background: 'var(--surface)',
                  border: '1px solid var(--border)',
                  color: 'var(--text)',
                  cursor: 'pointer',
                  padding: '0.5rem 0.75rem',
                  borderRadius: '6px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  fontSize: '0.875rem',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'var(--accent)';
                  e.currentTarget.style.borderColor = 'var(--accent)';
                  e.currentTarget.style.color = 'white';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'var(--surface)';
                  e.currentTarget.style.borderColor = 'var(--border)';
                  e.currentTarget.style.color = 'var(--text)';
                }}
              >
                <svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"/>
                </svg>
                Open Backup Folder
              </button>
            </div>
          </div>

      {/* Quick Actions */}
      <div className="quick-actions">
        <button className="action-btn" onClick={forceBackup}>
          <svg className="action-icon" fill="currentColor" viewBox="0 0 20 20">
            <path d="M4 3a2 2 0 100 4h12a2 2 0 100-4H4z"/>
            <path fillRule="evenodd" d="M3 8h14v7a2 2 0 01-2 2H5a2 2 0 01-2-2V8zm5 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" clipRule="evenodd"/>
          </svg>
          Force Backup
        </button>
        <button className="action-btn" onClick={() => showNotification('Opening restore interface...')}>
          <svg className="action-icon" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd"/>
          </svg>
          Restore File
        </button>
        <button className="action-btn" onClick={() => handleProjectSettings(selectedProject)}>
          <svg className="action-icon" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd"/>
          </svg>
          Settings
        </button>
        <button className="action-btn" onClick={() => showNotification('Press ? for keyboard shortcuts')}>
          <svg className="action-icon" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd"/>
          </svg>
          Help <kbd>?</kbd>
        </button>
      </div>

      {/* Main Grid */}
      <div className="main-grid">
        {/* Timeline Section */}
        <div className="timeline-section">
          <div className="timeline-header">
            <div className="timeline-title">
              Backup Activity
              <span className="timeline-badge">LIVE</span>
            </div>
            <div className="timeline-controls">
              <button
                className={`timeline-btn ${timeRange === '1h' ? 'active' : ''}`}
                onClick={() => setTimeRange('1h')}
              >
                1H
              </button>
              <button
                className={`timeline-btn ${timeRange === '6h' ? 'active' : ''}`}
                onClick={() => setTimeRange('6h')}
              >
                6H
              </button>
              <button
                className={`timeline-btn ${timeRange === '24h' ? 'active' : ''}`}
                onClick={() => setTimeRange('24h')}
              >
                24H
              </button>
              <button
                className={`timeline-btn ${timeRange === '7d' ? 'active' : ''}`}
                onClick={() => setTimeRange('7d')}
              >
                7D
              </button>
            </div>
          </div>
          <div className="timeline-graph">
            <svg className="graph-container" viewBox="0 0 400 120" preserveAspectRatio="none">
              <defs>
                <linearGradient id="gradient" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" style={{ stopColor: '#4ade80', stopOpacity: 0.3 }} />
                  <stop offset="100%" style={{ stopColor: '#4ade80', stopOpacity: 0 }} />
                </linearGradient>
              </defs>
              {/* Grid lines */}
              <path className="graph-grid" d="M 0 30 L 400 30 M 0 60 L 400 60 M 0 90 L 400 90"/>
              <path className="graph-grid" d="M 100 0 L 100 120 M 200 0 L 200 120 M 300 0 L 300 120"/>
              {/* Data */}
              <path className="graph-fill" d={graphFillPath} fill="url(#gradient)"/>
              <path className="graph-line" d={graphLinePath}/>
              <circle className="graph-dot" cx="400" cy={120 - graphData[graphData.length - 1]} r="4"/>
            </svg>
          </div>
          <div className="time-labels">
            {getTimeLabels().map((label, index) => (
              <span key={index}>{label}</span>
            ))}
          </div>
        </div>

        {/* File Monitor */}
        <div className="file-monitor">
          <div className="monitor-header">
            <h3 className="monitor-title">Protection Status</h3>
            <div className="next-backup">
              <svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd"/>
              </svg>
              {isWatching ? (
                <>
                  Next backup in <span className="next-backup-time">
                    {Math.floor(countdown / 60)}m {countdown % 60}s
                  </span>
                </>
              ) : (
                <span className="next-backup-time">No folder linked</span>
              )}
            </div>
            <div className="backup-progress">
              <div
                className="backup-progress-bar"
                style={{ width: `${((1200 - countdown) / 1200) * 100}%` }}
              />
            </div>
          </div>
          <div className="file-stats">
            <div className="stat-row">
              <span className="stat-label">
                <svg className="stat-icon" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
                </svg>
                Protected
              </span>
              <span className="stat-value">{stats.protectedCount.toLocaleString()}</span>
            </div>
            <div className="stat-row">
              <span className="stat-label">
                <svg className="stat-icon" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/>
                </svg>
                Modified
              </span>
              <span className="stat-value" style={{ color: 'var(--warning)' }}>
                {stats.modifiedCount}
              </span>
            </div>
            <div className="stat-row">
              <span className="stat-label">
                <svg className="stat-icon" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd"/>
                </svg>
                Stale
              </span>
              <span className="stat-value" style={{ color: 'var(--danger)' }}>
                {stats.staleCount}
              </span>
            </div>
            <div className="stat-row">
              <span className="stat-label">
                <svg className="stat-icon" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M3 7v10a2 2 0 002 2h10a2 2 0 002-2V9a2 2 0 00-2-2h-2l-2-2H5a2 2 0 00-2 2z"/>
                </svg>
                Total Size
              </span>
              <span className="stat-value">{stats.totalSize}</span>
            </div>
            <div className="stat-row">
              <span className="stat-label">
                <svg className="stat-icon" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd"/>
                </svg>
                Recoveries
              </span>
              <span className="stat-value">{stats.recoveriesCount}</span>
            </div>
          </div>
          <div className="storage-gauge">
            <div className="gauge-header">
              <span className="gauge-title">Storage Used</span>
              <span className="gauge-value">{stats.storagePercent}% of 0GB</span>
            </div>
            <div className="gauge-bar">
              <div className="gauge-fill" style={{ width: `${stats.storagePercent}%` }} />
            </div>
          </div>
        </div>
      </div>

      {/* Patterns Section */}
      <div className="patterns-card">
        <h3 className="monitor-title" style={{ marginBottom: '1rem' }}>AI-Detected Patterns</h3>
        <div className="pattern-item">
          <span className="pattern-text">
            <svg className="pattern-icon" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd"/>
            </svg>
            Peak save time
          </span>
          <span className="pattern-value">{stats.peakTime}</span>
        </div>
        <div className="pattern-item">
          <span className="pattern-text">
            <svg className="pattern-icon" fill="currentColor" viewBox="0 0 20 20">
              <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"/>
            </svg>
            Most active directory
          </span>
          <span className="pattern-value">--</span>
        </div>
        <div className="pattern-item">
          <span className="pattern-text">
            <svg className="pattern-icon" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd"/>
            </svg>
            Average save interval
          </span>
          <span className="pattern-value">--</span>
        </div>
        <div className="pattern-item">
          <span className="pattern-text">
            <svg className="pattern-icon" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9 4.804A7.968 7.968 0 005.5 4c-1.255 0-2.443.29-3.5.804v10A7.969 7.969 0 015.5 14c1.669 0 3.218.51 4.5 1.385A7.962 7.962 0 0114.5 14c1.255 0 2.443.29 3.5.804v-10A7.968 7.968 0 0014.5 4c-1.255 0-2.443.29-3.5.804V12a1 1 0 11-2 0V4.804z"/>
            </svg>
            Backup efficiency
          </span>
          <span className="pattern-value">0%</span>
        </div>
      </div>

      {/* Files Section */}
      <div className="files-section">
        <div className="files-header">
          <h2 className="files-title">Active Files</h2>
          <div className="files-controls">
            <div className="search-box">
              <svg className="search-icon" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd"/>
              </svg>
              <input
                type="text"
                className="search-input"
                placeholder="Search files..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <div className="view-toggle">
              <button
                className={`toggle-btn ${fileView === 'recent' ? 'active' : ''}`}
                onClick={() => setFileView('recent')}
              >
                Recent
              </button>
              <button
                className={`toggle-btn ${fileView === 'modified' ? 'active' : ''}`}
                onClick={() => setFileView('modified')}
              >
                Modified
              </button>
              <button
                className={`toggle-btn ${fileView === 'all' ? 'active' : ''}`}
                onClick={() => setFileView('all')}
              >
                All
              </button>
            </div>
          </div>
        </div>

        <div className="files-list">
          {!isWatching ? (
            <div style={{
              padding: '3rem',
              textAlign: 'center',
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: '12px'
            }}>
              <svg width="48" height="48" fill="currentColor" viewBox="0 0 20 20" style={{
                margin: '0 auto 1rem',
                opacity: 0.3
              }}>
                <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"/>
              </svg>
              <p style={{ color: 'var(--text-dim)', marginBottom: '1.5rem' }}>
                No folder is currently being watched
              </p>
              <button
                className="action-btn"
                onClick={linkFolder}
                style={{
                  display: 'inline-flex',
                  width: 'auto',
                  padding: '0.75rem 2rem'
                }}
              >
                <svg className="action-icon" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M8 5a1 1 0 011 1v1h6a2 2 0 012 2v7a2 2 0 01-2 2H5a2 2 0 01-2-2V9a2 2 0 012-2h1V6a1 1 0 011-1h2zm2 2V6H8v1h2z"/>
                </svg>
                Link Folder
              </button>
            </div>
          ) : filteredFiles.length === 0 ? (
            <div style={{
              padding: '2rem',
              textAlign: 'center',
              color: 'var(--text-dim)',
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: '8px'
            }}>
              No files have been modified yet
            </div>
          ) : filteredFiles.map((file, index) => (
            <div
              key={index}
              className="file-item"
              onClick={() => handleFileClick(file.path)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '1rem 1.25rem',
                background: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                marginBottom: '0.5rem',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'var(--border-hover)';
                e.currentTarget.style.transform = 'translateX(2px)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--border)';
                e.currentTarget.style.transform = 'translateX(0)';
              }}
            >
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                flex: 1,
                minWidth: 0
              }}>
                <span className={`file-status ${file.status === 'modified' ? 'modified' : ''}`}
                  style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    background: file.status === 'modified' ? 'var(--accent)' : 'var(--text-dim)',
                    flexShrink: 0
                  }}
                />
                <span style={{
                  color: 'var(--text)',
                  fontSize: '0.9375rem',
                  fontFamily: 'monospace',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap'
                }}>
                  {file.path}
                </span>
              </div>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '1rem',
                flexShrink: 0
              }}>
                <span style={{
                  color: 'var(--text-dim)',
                  fontSize: '0.875rem',
                  fontWeight: 500
                }}>
                  {file.timeAgo}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Footer Stats */}
      <footer className="footer-stats">
        <div className="footer-stat" onClick={() => showNotification('Loading storage analytics...')}>
          <div className="footer-number">0</div>
          <div className="footer-label">GB Protected</div>
        </div>
        <div className="footer-stat" onClick={() => showNotification('Loading backup history...')}>
          <div className="footer-number">0</div>
          <div className="footer-label">Total Backups</div>
        </div>
        <div className="footer-stat" onClick={() => showNotification('Loading uptime report...')}>
          <div className="footer-number">0%</div>
          <div className="footer-label">Uptime</div>
        </div>
        <div className="footer-stat" onClick={() => showNotification('No data loss events!')}>
          <div className="footer-number">0</div>
          <div className="footer-label">Data Lost</div>
        </div>
      </footer>

      {/* History Modal */}
      {showHistoryModal && (
        <div className="history-modal show">
          <div className="history-content">
            <div className="history-header">
              <h2 className="history-title">History: {selectedFile}</h2>
              <button className="close-btn" onClick={() => setShowHistoryModal(false)}>
                <svg width="24" height="24" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd"/>
                </svg>
              </button>
            </div>
            <div className="history-body">
              <div className="history-timeline">
                {generateHistory().map((entry, index) => (
                  <div key={index} className="history-entry">
                    <div className="history-line">
                      <div
                        className="history-dot"
                        style={index === 0 ? { background: 'var(--accent)' } : {}}
                      />
                    </div>
                    <div className="history-details">
                      <div className="history-time">{entry.time}</div>
                      <div className="history-changes">{entry.changes}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Floating Backup Indicator */}
      <div
        className={`backup-indicator ${backupIndicatorActive ? 'active' : ''}`}
        onClick={forceBackup}
      >
        <svg className="backup-icon" fill="#4ade80" viewBox="0 0 20 20">
          <path d="M4 3a2 2 0 100 4h12a2 2 0 100-4H4z"/>
          <path fillRule="evenodd" d="M3 8h14v7a2 2 0 01-2 2H5a2 2 0 01-2-2V8zm5 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" clipRule="evenodd"/>
        </svg>
      </div>


      {/* Notification Toast */}
      <div
        className={`notification ${notification.show ? 'show' : ''}`}
        style={{
          ...(notification.type === 'error' && {
            background: 'rgba(220, 38, 38, 0.1)',
            borderColor: 'rgba(220, 38, 38, 0.3)'
          }),
          ...(notification.type === 'info' && {
            background: 'rgba(59, 130, 246, 0.1)',
            borderColor: 'rgba(59, 130, 246, 0.3)'
          })
        }}
      >
        <svg className="notification-icon" fill="currentColor" viewBox="0 0 20 20">
          {notification.type === 'error' ? (
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd"/>
          ) : notification.type === 'info' ? (
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd"/>
          ) : (
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
          )}
        </svg>
        <span
          className="notification-text"
          style={{
            ...(notification.type === 'error' && { color: 'rgba(220, 38, 38, 0.9)' }),
            ...(notification.type === 'info' && { color: 'rgba(59, 130, 246, 0.9)' })
          }}
        >
          {notification.message}
        </span>
      </div>
        </>
      )}

      {/* Configuration Dialog - Moved outside of details view */}
      {(() => {
        console.log('[DEBUG RENDER] showConfigDialog:', showConfigDialog, 'pendingProjectPath:', pendingProjectPath);
        return null;
      })()}
      {showConfigDialog && (
        <div className="modal-overlay" style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.95)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '2rem'
        }}>
          <div className="config-dialog" style={{
            background: 'var(--card-bg)',
            borderRadius: '12px',
            width: '500px',
            maxWidth: '90%',
            maxHeight: '85vh',
            border: '1px solid var(--border)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden'
          }}>
            <div style={{
              padding: '2rem 2rem 0 2rem',
              borderBottom: '1px solid var(--border)'
            }}>
              <h2 style={{ marginBottom: '1rem', color: 'var(--text)' }}>
                Configure Backup Settings
              </h2>
              <div style={{ fontSize: '0.875rem', color: 'var(--text-dim)', marginBottom: '1.5rem' }}>
                Project: <strong>{pendingProjectPath?.split('/').pop()}</strong>
              </div>
            </div>

            <div style={{
              flex: 1,
              overflowY: 'auto',
              padding: '2rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '1.25rem'
            }}>
              {/* Backup Interval */}
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', color: 'var(--text)' }}>
                  Backup Interval (minutes)
                </label>
                <input
                  type="number"
                  min="1"
                  max="1440"
                  value={projectConfig.interval}
                  onChange={(e) => setProjectConfig(prev => ({ ...prev, interval: parseInt(e.target.value) || 20 }))}
                  style={{
                    width: '100%',
                    padding: '0.5rem',
                    background: 'var(--input-bg)',
                    border: '1px solid var(--border)',
                    borderRadius: '6px',
                    color: 'var(--text)',
                    fontSize: '0.875rem'
                  }}
                />
                <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>
                  How often to create automatic backups (default: 20 minutes)
                </div>
              </div>

              {/* Compression Level */}
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', color: 'var(--text)' }}>
                  Compression Level
                </label>
                <input
                  type="range"
                  min="0"
                  max="9"
                  value={projectConfig.compression}
                  onChange={(e) => setProjectConfig(prev => ({ ...prev, compression: parseInt(e.target.value) }))}
                  style={{ width: '100%' }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                  <span>0 (None)</span>
                  <span style={{ color: 'var(--accent)' }}>Current: {projectConfig.compression}</span>
                  <span>9 (Max)</span>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.5rem' }}>
                  <strong>Compression levels:</strong><br/>
                  • 0: No compression (fastest, most space)<br/>
                  • 1-3: Fast compression (good for large files)<br/>
                  • 4-6: Balanced (recommended, default: 6)<br/>
                  • 7-9: Maximum compression (slowest, least space)
                </div>
              </div>

              {/* Backup Mode Options */}
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', color: 'var(--text)' }}>
                  Backup Mode
                </label>

                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={projectConfig.smartMode}
                    onChange={(e) => setProjectConfig(prev => ({ ...prev, smartMode: e.target.checked }))}
                  />
                  <span style={{ fontSize: '0.875rem', color: 'var(--text)' }}>Smart Mode</span>
                </label>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginLeft: '1.5rem', marginBottom: '0.75rem' }}>
                  Only backup after actual file changes (ignores pure save events)
                </div>

                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={projectConfig.incremental}
                    onChange={(e) => setProjectConfig(prev => ({ ...prev, incremental: e.target.checked }))}
                  />
                  <span style={{ fontSize: '0.875rem', color: 'var(--text)' }}>Incremental Backups</span>
                </label>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginLeft: '1.5rem', marginBottom: '0.75rem' }}>
                  Only save changes since last backup (saves space and time)
                </div>

                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={projectConfig.excludeGit}
                    onChange={(e) => setProjectConfig(prev => ({ ...prev, excludeGit: e.target.checked }))}
                  />
                  <span style={{ fontSize: '0.875rem', color: 'var(--text)' }}>Exclude .git Directory</span>
                </label>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginLeft: '1.5rem' }}>
                  Don't backup git repository data (saves significant space)
                </div>
              </div>

              {/* Persistence Options */}
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', color: 'var(--text)' }}>
                  Backup Persistence
                </label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <label style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.75rem',
                    background: projectConfig.persistence === 'always' ? 'var(--surface)' : 'transparent',
                    border: `1px solid ${projectConfig.persistence === 'always' ? 'var(--accent)' : 'var(--border)'}`,
                    borderRadius: '6px',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}>
                    <input
                      type="radio"
                      name="persistence"
                      value="always"
                      checked={projectConfig.persistence === 'always'}
                      onChange={(e) => setProjectConfig(prev => ({ ...prev, persistence: 'always' }))}
                    />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: '0.875rem', color: 'var(--text)', fontWeight: 500 }}>
                        Always run in background
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.125rem' }}>
                        Project will be added to the daemon and restart automatically
                      </div>
                    </div>
                  </label>

                  <label style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.75rem',
                    background: projectConfig.persistence === 'session' ? 'var(--surface)' : 'transparent',
                    border: `1px solid ${projectConfig.persistence === 'session' ? 'var(--accent)' : 'var(--border)'}`,
                    borderRadius: '6px',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}>
                    <input
                      type="radio"
                      name="persistence"
                      value="session"
                      checked={projectConfig.persistence === 'session'}
                      onChange={(e) => setProjectConfig(prev => ({ ...prev, persistence: 'session' }))}
                    />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: '0.875rem', color: 'var(--text)', fontWeight: 500 }}>
                        This session only
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.125rem' }}>
                        Stops watching when you close the app
                      </div>
                    </div>
                  </label>
                </div>
              </div>
            </div>

            {/* Action Buttons - Outside scrollable area */}
            <div style={{
              padding: '1.5rem 2rem',
              borderTop: '1px solid var(--border)',
              display: 'flex',
              gap: '1rem'
            }}>
              <button
                onClick={() => {
                  setShowConfigDialog(false);
                  setPendingProjectPath(null);
                }}
                style={{
                  flex: 1,
                  padding: '0.75rem',
                  background: 'transparent',
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  color: 'var(--text-dim)',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  transition: 'all 0.2s'
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleConfigSubmit}
                style={{
                  flex: 1,
                  padding: '0.75rem',
                  background: 'var(--accent)',
                  border: 'none',
                  borderRadius: '8px',
                  color: 'white',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  transition: 'all 0.2s'
                }}
              >
                Start Watching
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Notification Toast - Also moved outside */}
      <div
        className={`notification ${notification.show ? 'show' : ''}`}
        style={{
          ...(notification.type === 'error' && {
            background: 'rgba(220, 38, 38, 0.1)',
            borderColor: 'rgba(220, 38, 38, 0.3)'
          }),
          ...(notification.type === 'info' && {
            background: 'rgba(59, 130, 246, 0.1)',
            borderColor: 'rgba(59, 130, 246, 0.3)'
          })
        }}
      >
        <svg className="notification-icon" fill="currentColor" viewBox="0 0 20 20">
          {notification.type === 'error' ? (
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd"/>
          ) : notification.type === 'info' ? (
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd"/>
          ) : (
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
          )}
        </svg>
        <span
          className="notification-text"
          style={{
            ...(notification.type === 'error' && { color: 'rgba(220, 38, 38, 0.9)' }),
            ...(notification.type === 'info' && { color: 'rgba(59, 130, 246, 0.9)' })
          }}
        >
          {notification.message}
        </span>
      </div>

      {/* Project Overlap Dialog */}
      {showOverlapDialog && overlapInfo && (
        <div className="modal-overlay" style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.95)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1001
        }}>
          <div style={{
            background: 'var(--card-bg)',
            borderRadius: '12px',
            padding: '2rem',
            width: '500px',
            maxWidth: '90%',
            border: '1px solid var(--border)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
              <svg width="32" height="32" fill="currentColor" viewBox="0 0 20 20" style={{ color: 'var(--warning)' }}>
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd"/>
              </svg>
              <h2 style={{ margin: 0, fontSize: '1.25rem', color: 'var(--text-bright)' }}>
                Project Overlap Detected
              </h2>
            </div>

            <div style={{ marginBottom: '1.5rem' }}>
              {overlapInfo.overlaps.map((overlap, index) => (
                <div key={index} style={{
                  padding: '1rem',
                  background: 'var(--surface)',
                  borderRadius: '8px',
                  marginBottom: '0.75rem',
                  border: '1px solid var(--border)'
                }}>
                  <p style={{ margin: 0, marginBottom: '0.5rem', color: 'var(--text)' }}>
                    {overlap.message}
                  </p>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    fontSize: '0.875rem',
                    color: 'var(--text-dim)'
                  }}>
                    <svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"/>
                    </svg>
                    <span style={{ fontFamily: 'var(--mono)' }}>{overlap.existingPath}</span>
                  </div>
                </div>
              ))}
            </div>

            <p style={{ marginBottom: '1.5rem', color: 'var(--text-dim)', fontSize: '0.875rem' }}>
              Would you like to replace the existing project{overlapInfo.overlaps.length > 1 ? 's' : ''} with "{overlapInfo.newName}",
              or keep watching both?
            </p>

            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button
                onClick={() => {
                  setShowOverlapDialog(false);
                  setShowConfigDialog(true);
                }}
                style={{
                  flex: 1,
                  padding: '0.75rem',
                  background: 'transparent',
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  color: 'var(--text-dim)',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  transition: 'all 0.2s'
                }}
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  setShowOverlapDialog(false);
                  showNotification('Keeping all projects...', 'info');
                  // Continue with watching the new project anyway
                  try {
                    const overlappingPaths = overlapInfo.overlaps.map(o => o.existingPath);
                    await (window as any).saviorAPI.removeAndWatch(
                      [],  // Don't remove any projects
                      overlapInfo.newPath,
                      projectConfig
                    );
                    setIsWatching(true);
                    setCurrentProject(overlapInfo.newPath);
                    setStats(prev => ({ ...prev, projectCount: prev.projectCount + 1 }));
                    showNotification(`Now watching: ${overlapInfo.newName}`, 'success');
                    setPendingProjectPath(null);
                    setOverlapInfo(null);
                  } catch (error: any) {
                    showNotification('Failed to start watching project', 'error');
                    setShowConfigDialog(true);
                  }
                }}
                style={{
                  flex: 1,
                  padding: '0.75rem',
                  background: 'transparent',
                  border: '1px solid var(--accent)',
                  borderRadius: '8px',
                  color: 'var(--accent)',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  transition: 'all 0.2s'
                }}
              >
                Keep Both
              </button>
              <button
                onClick={async () => {
                  setShowOverlapDialog(false);
                  const overlappingPaths = overlapInfo.overlaps.map(o => o.existingPath);
                  showNotification(`Replacing ${overlappingPaths.length} project${overlappingPaths.length > 1 ? 's' : ''}...`, 'info');

                  try {
                    await (window as any).saviorAPI.removeAndWatch(
                      overlappingPaths,
                      overlapInfo.newPath,
                      projectConfig
                    );
                    setIsWatching(true);
                    setCurrentProject(overlapInfo.newPath);
                    showNotification(`Now watching: ${overlapInfo.newName}`, 'success');
                    setPendingProjectPath(null);
                    setOverlapInfo(null);
                  } catch (error: any) {
                    showNotification('Failed to replace projects', 'error');
                    setShowConfigDialog(true);
                  }
                }}
                style={{
                  flex: 1.5,
                  padding: '0.75rem',
                  background: 'var(--accent)',
                  border: 'none',
                  borderRadius: '8px',
                  color: 'white',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  transition: 'all 0.2s'
                }}
              >
                Replace with New
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Project Settings Modal */}
      {showProjectSettings && settingsProject && (
        <div className="modal-overlay" style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.95)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1002
        }}>
          <div style={{
            background: 'var(--card-bg)',
            borderRadius: '16px',
            width: '600px',
            maxWidth: '90%',
            maxHeight: '90vh',
            overflow: 'hidden',
            border: '1px solid var(--border)',
            display: 'flex',
            flexDirection: 'column'
          }}>
            {/* Header */}
            <div style={{
              padding: '2rem',
              borderBottom: '1px solid var(--border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <div>
                <h2 style={{
                  margin: 0,
                  fontSize: '1.5rem',
                  fontWeight: 600,
                  color: 'var(--text-bright)',
                  marginBottom: '0.25rem'
                }}>
                  Project Settings
                </h2>
                <p style={{
                  margin: 0,
                  fontSize: '0.875rem',
                  color: 'var(--text-dim)'
                }}>
                  Configure backup behavior for {settingsProject.name}
                </p>
              </div>
              <button
                onClick={() => setShowProjectSettings(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  padding: '0.5rem',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  color: 'var(--text-dim)',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'var(--surface)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'none'}
              >
                <svg width="24" height="24" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd"/>
                </svg>
              </button>
            </div>

            {/* Content */}
            <div style={{
              padding: '2rem',
              overflow: 'auto',
              flex: 1
            }}>
              {/* Project Info Card */}
              <div style={{
                background: 'var(--surface)',
                borderRadius: '12px',
                padding: '1.25rem',
                marginBottom: '2rem',
                border: '1px solid var(--border)'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  <div style={{
                    width: '48px',
                    height: '48px',
                    background: 'var(--accent)',
                    borderRadius: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    opacity: 0.9
                  }}>
                    <svg width="28" height="28" fill="white" viewBox="0 0 20 20">
                      <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"/>
                    </svg>
                  </div>
                  <div style={{ flex: 1 }}>
                    <h3 style={{
                      margin: 0,
                      fontSize: '1.125rem',
                      fontWeight: 600,
                      color: 'var(--text-bright)',
                      marginBottom: '0.25rem'
                    }}>
                      {settingsProject.name}
                    </h3>
                    <p style={{
                      margin: 0,
                      fontSize: '0.875rem',
                      color: 'var(--text-dim)',
                      fontFamily: 'var(--mono)'
                    }}>
                      {settingsProject.path}
                    </p>
                  </div>
                </div>
              </div>

              {/* Settings Form */}
              <SettingsForm
                initialConfig={{
                  interval: settingsProject.interval || 20,
                  smartMode: settingsProject.smartMode !== false,
                  incremental: settingsProject.incremental !== false,
                  compression: settingsProject.compression || 6,
                  excludeGit: settingsProject.excludeGit || false
                }}
                onSave={handleSaveProjectSettings}
                onCancel={() => setShowProjectSettings(false)}
                onStop={() => setShowStopConfirm(true)}
              />
            </div>
          </div>
        </div>
      )}

      {/* Stop Watching Confirmation Dialog */}
      {showStopConfirm && settingsProject && (
        <div className="modal-overlay" style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.95)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1003
        }}>
          <div style={{
            background: 'var(--card-bg)',
            borderRadius: '12px',
            padding: '2rem',
            width: '450px',
            maxWidth: '90%',
            border: '1px solid var(--border)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
              <svg width="32" height="32" fill="currentColor" viewBox="0 0 20 20" style={{ color: 'var(--danger)' }}>
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd"/>
              </svg>
              <h2 style={{ margin: 0, fontSize: '1.25rem', color: 'var(--text-bright)' }}>
                Stop Watching Project?
              </h2>
            </div>

            <p style={{ marginBottom: '0.5rem', color: 'var(--text)' }}>
              Are you sure you want to stop watching <strong>{settingsProject.name}</strong>?
            </p>
            <p style={{ marginBottom: '1.5rem', color: 'var(--text-dim)', fontSize: '0.875rem' }}>
              Automatic backups will stop for this project. You can always start watching it again later.
            </p>

            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button
                onClick={() => setShowStopConfirm(false)}
                style={{
                  flex: 1,
                  padding: '0.75rem',
                  background: 'transparent',
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  color: 'var(--text-dim)',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  fontWeight: 500,
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'var(--accent)';
                  e.currentTarget.style.color = 'var(--accent)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'var(--border)';
                  e.currentTarget.style.color = 'var(--text-dim)';
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleStopWatching}
                style={{
                  flex: 1,
                  padding: '0.75rem',
                  background: 'var(--danger)',
                  border: 'none',
                  borderRadius: '8px',
                  color: 'white',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.opacity = '0.9'}
                onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
              >
                Stop Watching
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Backup Contents Viewer */}
      {showBackupContents && selectedBackupPath && selectedProject && (
        <BackupContentsViewer
          backupPath={selectedBackupPath}
          projectName={selectedProject.name}
          onClose={() => {
            setShowBackupContents(false);
            setSelectedBackupPath(null);
          }}
        />
      )}
    </div>
  );
};

export default App;