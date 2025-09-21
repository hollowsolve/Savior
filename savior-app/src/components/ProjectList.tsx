import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FolderIcon,
  PlayIcon,
  StopIcon,
  ArrowPathIcon,
  TrashIcon,
  EllipsisVerticalIcon,
  PlusIcon,
  ClockIcon,
  ServerStackIcon,
  SparklesIcon,
  DocumentArrowDownIcon,
  ShieldCheckIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';
import { Menu } from '@headlessui/react';
import { useProjectStore } from '../stores/projectStore';
import { formatBytes, formatRelativeTime } from '../utils/format';

interface ProjectListProps {
  onSelectProject: (path: string) => void;
}

export const ProjectList: React.FC<ProjectListProps> = ({ onSelectProject }) => {
  const { projects, addProject, removeProject, toggleProject, refreshProjects } = useProjectStore();
  const [isAdding, setIsAdding] = useState(false);
  const [hoveredProject, setHoveredProject] = useState<string | null>(null);

  const handleAddProject = async () => {
    setIsAdding(true);
    try {
      const path = await window.saviorAPI.selectDirectory();
      if (path) {
        await addProject(path);
      }
    } finally {
      setIsAdding(false);
    }
  };

  const handleToggleProject = async (path: string, active: boolean) => {
    await toggleProject(path, !active);
  };

  const handleForceBackup = async (path: string) => {
    await window.saviorAPI.saveBackup(path, 'Manual backup from Savior app');
  };

  const handleRemoveProject = async (path: string) => {
    if (confirm(`Remove ${path} from Savior?`)) {
      await removeProject(path);
    }
  };

  // Calculate project health
  const getProjectHealth = (project: any) => {
    if (!project.lastBackup) return 'new';
    const hoursSinceBackup = (Date.now() - new Date(project.lastBackup).getTime()) / (1000 * 60 * 60);
    if (hoursSinceBackup < 1) return 'excellent';
    if (hoursSinceBackup < 24) return 'good';
    if (hoursSinceBackup < 72) return 'warning';
    return 'critical';
  };

  const getHealthIcon = (health: string) => {
    switch (health) {
      case 'excellent':
      case 'good':
        return <ShieldCheckIcon className="w-5 h-5 text-success" />;
      case 'warning':
        return <ExclamationTriangleIcon className="w-5 h-5 text-yellow-400" />;
      case 'critical':
        return <ExclamationTriangleIcon className="w-5 h-5 text-red-400" />;
      default:
        return <SparklesIcon className="w-5 h-5 text-info" />;
    }
  };

  const getHealthMessage = (health: string) => {
    switch (health) {
      case 'excellent':
        return 'Fully protected';
      case 'good':
        return 'Recently backed up';
      case 'warning':
        return 'Backup recommended';
      case 'critical':
        return 'Needs backup soon';
      default:
        return 'Ready to protect';
    }
  };

  return (
    <div className="p-8 w-full">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8 text-center">
          <motion.h1
            className="text-3xl font-bold text-white mb-2"
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            {projects.length === 0 ? "Let's Protect Your Work" : "Your Guardian Dashboard"}
          </motion.h1>
          <motion.p
            className="text-gray-400"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1 }}
          >
            {projects.length === 0
              ? "Every great project deserves a guardian angel"
              : `🛡 Watching over ${projects.filter(p => p.active).length} ${projects.filter(p => p.active).length === 1 ? 'project' : 'projects'} | ${projects.length} total under protection`}
          </motion.p>
        </div>

      {/* Quick Stats */}
      {projects.length > 0 && (
        <div className="grid grid-cols-4 gap-4 mb-8">
          <motion.div
            whileHover={{ scale: 1.05, rotateY: 5 }}
            whileTap={{ scale: 0.98 }}
            transition={{ type: "spring", stiffness: 300 }}
            className="glass-card bg-gradient-to-br from-green-500/10 to-green-600/10 border border-green-500/20 rounded-xl p-4 cursor-pointer glass-shine"
          >
            <div className="flex items-center gap-3">
              <ShieldCheckIcon className="w-8 h-8 text-success" />
              <div>
                <p className="text-2xl font-bold text-white">
                  {projects.filter(p => p.active).length}
                </p>
                <p className="text-sm text-gray-400">Protected</p>
              </div>
            </div>
          </motion.div>

          <motion.div
            whileHover={{ scale: 1.05, rotateY: 5 }}
            whileTap={{ scale: 0.98 }}
            transition={{ type: "spring", stiffness: 300 }}
            className="glass-card bg-gradient-to-br from-blue-500/10 to-blue-600/10 border border-blue-500/20 rounded-xl p-4 cursor-pointer glass-shine"
          >
            <div className="flex items-center gap-3">
              <ServerStackIcon className="w-8 h-8 text-info" />
              <div>
                <p className="text-2xl font-bold text-white">
                  {projects.reduce((acc, p) => acc + p.backupCount, 0)}
                </p>
                <p className="text-sm text-gray-400">Total Backups</p>
              </div>
            </div>
          </motion.div>

          <motion.div
            whileHover={{ scale: 1.05, rotateY: 5 }}
            whileTap={{ scale: 0.98 }}
            transition={{ type: "spring", stiffness: 300 }}
            className="glass-card bg-gradient-to-br from-purple-500/10 to-purple-600/10 border border-purple-500/20 rounded-xl p-4 cursor-pointer glass-shine"
          >
            <div className="flex items-center gap-3">
              <ClockIcon className="w-8 h-8 text-accent-purple" />
              <div>
                <p className="text-2xl font-bold text-white">20m</p>
                <p className="text-sm text-gray-400">Auto-save</p>
              </div>
            </div>
          </motion.div>

          <motion.div
            whileHover={{ scale: 1.05, rotateY: 5 }}
            whileTap={{ scale: 0.98 }}
            transition={{ type: "spring", stiffness: 300 }}
            className="glass-card bg-gradient-to-br from-amber-500/10 to-amber-600/10 border border-amber-500/20 rounded-xl p-4 cursor-pointer glass-shine"
          >
            <div className="flex items-center gap-3">
              <DocumentArrowDownIcon className="w-8 h-8 text-warning" />
              <div>
                <p className="text-2xl font-bold text-white">
                  {formatBytes(projects.reduce((acc, p) => acc + p.size, 0))}
                </p>
                <p className="text-sm text-gray-400">Under Watch</p>
              </div>
            </div>
          </motion.div>
        </div>
      )}

      {/* Projects Grid */}
      {projects.length === 0 ? (
        <div className="flex justify-center items-center min-h-[400px]">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-gradient-to-br from-blue-500/5 to-purple-500/5 border border-blue-500/10 rounded-2xl p-12 max-w-2xl w-full flex flex-col items-center"
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", stiffness: 200 }}
              className="w-24 h-24 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center mb-6"
            >
              <FolderIcon className="w-12 h-12 text-white" />
            </motion.div>

            <h3 className="text-2xl font-bold text-white mb-3 text-center">
              Start Protecting Your Work
            </h3>
            <p className="text-gray-400 mb-8 text-center max-w-md">
              Add your first project and Savior will automatically backup your work every 20 minutes.
              Never lose progress again!
            </p>

            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleAddProject}
              className="btn-primary px-8 py-3 rounded-xl font-semibold animate-gradient"
            >
              <PlusIcon className="w-5 h-5" />
              Add Your First Project
            </motion.button>
          </motion.div>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Add Project Button */}
          <motion.button
            whileHover={{ scale: 1.02, borderRadius: '20px' }}
            whileTap={{ scale: 0.98 }}
            transition={{ type: "spring", stiffness: 400 }}
            onClick={handleAddProject}
            disabled={isAdding}
            className="w-full glass-card border-2 border-dashed border-gray-600 hover:border-blue-500 rounded-xl p-6 transition-all group overflow-hidden"
          >
            <div className="flex items-center justify-center gap-3">
              <div className="w-10 h-10 bg-blue-500/10 group-hover:bg-blue-500/20 rounded-lg flex items-center justify-center transition-colors">
                <ShieldCheckIcon className="w-5 h-5 text-savior-red" />
              </div>
              <span className="text-gray-400 group-hover:text-white transition-colors font-medium">
                Add New Project
              </span>
            </div>
          </motion.button>

          {/* Project Cards */}
          <AnimatePresence>
            {projects.map((project, index) => {
              const health = getProjectHealth(project);
              const isHovered = hoveredProject === project.path;

              return (
                <motion.div
                  key={project.path}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ delay: index * 0.05, type: "spring", stiffness: 300 }}
                  whileHover={{ y: -4, scale: 1.01 }}
                  onMouseEnter={() => setHoveredProject(project.path)}
                  onMouseLeave={() => setHoveredProject(null)}
                  className={`relative glass-card ${
                    project.active ? 'border-green-500/40 animate-glow' : 'border-gray-700/50'
                  } rounded-xl p-6 transition-all overflow-hidden ${
                    isHovered ? 'shadow-2xl shadow-black/50' : ''
                  }`}
                >
                  {/* Active Indicator */}
                  {project.active && (
                    <>
                      <div className="absolute -top-px left-8 right-8 h-px bg-gradient-to-r from-transparent via-green-400 to-transparent shimmer" />
                      <div className="absolute inset-0 bg-gradient-to-r from-green-500/5 via-transparent to-green-500/5 pointer-events-none" />
                    </>
                  )}

                  <div className="flex items-start justify-between">
                    {/* Project Info */}
                    <div className="flex-1 flex items-start gap-4">
                      <div className={`p-3 rounded-xl ${
                        project.active
                          ? 'bg-gradient-to-br from-green-500/20 to-green-600/10'
                          : 'bg-gray-700/50'
                      }`}>
                        <FolderIcon className={`w-6 h-6 ${
                          project.active ? 'text-success' : 'text-text-tertiary'
                        }`} />
                      </div>

                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-1">
                          <h3 className="text-lg font-semibold text-white">
                            {project.name}
                          </h3>
                          {getHealthIcon(health)}
                        </div>

                        <p className="text-sm text-gray-500 font-mono mb-3">
                          {project.path}
                        </p>

                        <div className="flex items-center gap-4 text-sm">
                          <div className="flex items-center gap-1.5">
                            <ClockIcon className="w-4 h-4 text-gray-500" />
                            <span className="text-gray-400">
                              {project.lastBackup
                                ? formatRelativeTime(project.lastBackup)
                                : 'Never backed up'}
                            </span>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <ServerStackIcon className="w-4 h-4 text-gray-500" />
                            <span className="text-gray-400">
                              {project.backupCount} saves
                            </span>
                          </div>
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                            health === 'excellent' || health === 'good' ? 'bg-success/20 text-success' :
                            health === 'warning' ? 'bg-warning/20 text-warning' :
                            health === 'critical' ? 'bg-danger/20 text-danger' :
                            'bg-info/20 text-info'
                          }`}>
                            {getHealthMessage(health)}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      <motion.button
                        whileHover={{ scale: 1.08 }}
                        whileTap={{ scale: 0.92 }}
                        transition={{ type: "spring", stiffness: 400 }}
                        onClick={() => handleToggleProject(project.path, project.active)}
                        className={`px-4 py-2 rounded-lg font-medium transition-all ${
                          project.active
                            ? 'bg-gray-700/70 hover:bg-gray-600 text-gray-300 backdrop-blur'
                            : 'btn-primary'
                        }`}
                      >
                        {project.active ? 'Pause' : 'Protect'}
                      </motion.button>

                      <Menu as="div" className="relative">
                        <Menu.Button className="p-2 hover:bg-gray-700 rounded-lg transition-colors">
                          <EllipsisVerticalIcon className="w-5 h-5 text-gray-400" />
                        </Menu.Button>

                        <Menu.Items className="absolute right-0 mt-2 w-56 bg-gray-800 rounded-xl shadow-2xl border border-gray-700 overflow-hidden z-10">
                          <Menu.Item>
                            {({ active }) => (
                              <button
                                onClick={() => onSelectProject(project.path)}
                                className={`${
                                  active ? 'bg-gray-700' : ''
                                } w-full text-left px-4 py-3 text-sm text-white flex items-center gap-3 transition-colors`}
                              >
                                <ClockIcon className="w-4 h-4 text-gray-400" />
                                View Backup History
                              </button>
                            )}
                          </Menu.Item>

                          <Menu.Item>
                            {({ active }) => (
                              <button
                                onClick={() => handleForceBackup(project.path)}
                                disabled={!project.active}
                                className={`${
                                  active ? 'bg-gray-700' : ''
                                } w-full text-left px-4 py-3 text-sm text-white flex items-center gap-3 transition-colors disabled:opacity-50`}
                              >
                                <DocumentArrowDownIcon className="w-4 h-4 text-gray-400" />
                                Backup Now
                              </button>
                            )}
                          </Menu.Item>

                          <div className="border-t border-gray-700 my-1" />

                          <Menu.Item>
                            {({ active }) => (
                              <button
                                onClick={() => handleRemoveProject(project.path)}
                                className={`${
                                  active ? 'bg-red-500/10' : ''
                                } w-full text-left px-4 py-3 text-sm text-red-400 flex items-center gap-3 transition-colors`}
                              >
                                <TrashIcon className="w-4 h-4" />
                                Remove from Savior
                              </button>
                            )}
                          </Menu.Item>
                        </Menu.Items>
                      </Menu>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      )}
      </div>
    </div>
  );
};