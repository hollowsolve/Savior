import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  ArrowLeftIcon,
  ClockIcon,
  DocumentIcon,
  ArrowDownTrayIcon,
  TrashIcon,
  EyeIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';
import { formatBytes, formatDate } from '../utils/format';

interface BackupViewerProps {
  projectPath: string;
  onBack: () => void;
}

interface Backup {
  id: string;
  name: string;
  path: string;
  size: number;
  timestamp: number;
  date: string;
  description?: string;
}

export const BackupViewer: React.FC<BackupViewerProps> = ({ projectPath, onBack }) => {
  const [backups, setBackups] = useState<Backup[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedBackup, setSelectedBackup] = useState<Backup | null>(null);
  const [isRestoring, setIsRestoring] = useState(false);

  useEffect(() => {
    loadBackups();
  }, [projectPath]);

  const loadBackups = async () => {
    setLoading(true);
    try {
      const data = await window.saviorAPI.getBackups(projectPath);
      setBackups(data);
    } catch (error) {
      console.error('Failed to load backups:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRestore = async (backup: Backup) => {
    if (!confirm(`Restore backup from ${formatDate(backup.date)}? This will overwrite current files.`)) {
      return;
    }

    setIsRestoring(true);
    try {
      await window.saviorAPI.restoreBackup(projectPath, backup.id, {
        check_conflicts: true,
        force: false
      });
      alert('Backup restored successfully!');
    } catch (error) {
      alert(`Failed to restore backup: ${(error as any)?.message || error}`);
    } finally {
      setIsRestoring(false);
    }
  };

  const handleDelete = async (backup: Backup) => {
    if (!confirm(`Delete backup from ${formatDate(backup.date)}?`)) {
      return;
    }

    try {
      await window.saviorAPI.deleteBackup(projectPath, backup.id);
      await loadBackups();
    } catch (error) {
      alert(`Failed to delete backup: ${(error as any)?.message || error}`);
    }
  };

  const projectName = projectPath.split('/').pop() || projectPath;

  return (
    <div className="p-6">
      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={onBack}
          className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
        >
          <ArrowLeftIcon className="w-5 h-5" />
        </button>
        <div className="flex-1">
          <h2 className="text-xl font-semibold">{projectName} Backups</h2>
          <p className="text-sm text-gray-400">{projectPath}</p>
        </div>
        <button
          onClick={loadBackups}
          className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
        >
          <ArrowPathIcon className="w-5 h-5" />
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <ArrowPathIcon className="w-8 h-8 animate-spin text-gray-400" />
        </div>
      ) : backups.length === 0 ? (
        <div className="text-center py-12">
          <ClockIcon className="w-16 h-16 mx-auto mb-4 text-gray-600" />
          <h3 className="text-lg font-medium mb-2">No backups yet</h3>
          <p className="text-gray-500">
            Backups will appear here once Savior starts watching this project
          </p>
        </div>
      ) : (
        <div className="grid gap-3">
          {backups.map((backup) => (
            <motion.div
              key={backup.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className={`bg-gray-800 rounded-lg p-4 hover:bg-gray-750 transition-colors cursor-pointer ${
                selectedBackup?.id === backup.id ? 'ring-2 ring-blue-500' : ''
              }`}
              onClick={() => setSelectedBackup(backup)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <DocumentIcon className="w-8 h-8 text-blue-500" />
                  <div>
                    <h3 className="font-medium">
                      {backup.description || 'Automatic backup'}
                    </h3>
                    <div className="flex items-center gap-4 text-sm text-gray-400">
                      <span>{formatDate(backup.date)}</span>
                      <span>{formatBytes(backup.size)}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      // Preview functionality
                    }}
                    className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
                    title="Preview"
                  >
                    <EyeIcon className="w-5 h-5" />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRestore(backup);
                    }}
                    disabled={isRestoring}
                    className="p-2 bg-green-600 hover:bg-green-700 rounded-lg transition-colors disabled:opacity-50"
                    title="Restore"
                  >
                    <ArrowDownTrayIcon className="w-5 h-5" />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(backup);
                    }}
                    className="p-2 hover:bg-red-600 rounded-lg transition-colors"
                    title="Delete"
                  >
                    <TrashIcon className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
};