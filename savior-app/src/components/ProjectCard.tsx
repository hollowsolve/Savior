import React, { useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { formatDistanceToNow } from 'date-fns';
import {
  FolderIcon,
  ClockIcon,
  DocumentTextIcon,
  ArrowPathIcon,
  PauseIcon,
  PlayIcon,
  TrashIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline';

interface ProjectCardProps {
  project: {
    path: string;
    name: string;
    lastBackup?: string;
    fileCount: number;
    size: string;
    isActive: boolean;
    backupCount: number;
  };
  onSelect: (path: string) => void;
  onAction?: (action: 'pause' | 'resume' | 'delete' | 'stats', path: string) => void;
}

export const ProjectCard: React.FC<ProjectCardProps> = ({ project, onSelect, onAction }) => {
  const cardRef = useRef<HTMLDivElement>(null);
  const [isHovered, setIsHovered] = useState(false);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!cardRef.current) return;

    const rect = cardRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const centerX = rect.width / 2;
    const centerY = rect.height / 2;

    const rotateX = ((y - centerY) / centerY) * -10;
    const rotateY = ((x - centerX) / centerX) * 10;

    setMousePosition({ x: rotateX, y: rotateY });
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    setMousePosition({ x: 0, y: 0 });
  };

  const formatSize = (size: string) => {
    const num = parseFloat(size);
    if (num < 1024) return `${num} B`;
    if (num < 1024 * 1024) return `${(num / 1024).toFixed(1)} KB`;
    if (num < 1024 * 1024 * 1024) return `${(num / (1024 * 1024)).toFixed(1)} MB`;
    return `${(num / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  };

  return (
    <motion.div
      ref={cardRef}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.02 }}
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={handleMouseLeave}
      onClick={() => onSelect(project.path)}
      className="project-card relative overflow-hidden cursor-pointer"
      style={{
        transform: isHovered
          ? `perspective(1000px) rotateX(${mousePosition.x}deg) rotateY(${mousePosition.y}deg)`
          : 'none',
        transition: 'transform 0.1s ease-out'
      }}
    >
      {/* Gradient overlay on hover */}
      <motion.div
        className="absolute inset-0 bg-gradient-to-br from-savior-red/10 via-transparent to-accent-blue/10 opacity-0"
        animate={{ opacity: isHovered ? 1 : 0 }}
        transition={{ duration: 0.3 }}
      />

      {/* Status indicator */}
      <div className="absolute top-4 right-4">
        <div className={clsx(
          'project-status-dot',
          project.isActive ? 'active' : 'inactive'
        )} />
      </div>

      {/* Content */}
      <div className="relative z-10">
        {/* Header */}
        <div className="flex items-start gap-3 mb-4">
          <motion.div
            animate={{
              rotate: isHovered ? 360 : 0,
              scale: isHovered ? 1.1 : 1
            }}
            transition={{ duration: 0.5 }}
            className="p-3 bg-savior-surface-2 rounded-lg"
          >
            <FolderIcon className="w-6 h-6 text-savior-red" />
          </motion.div>

          <div className="flex-1">
            <h3 className="font-semibold text-lg text-text-primary mb-1">
              {project.name}
            </h3>
            <p className="text-xs text-text-tertiary font-mono truncate">
              {project.path}
            </p>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="flex items-center gap-2">
            <ClockIcon className="w-4 h-4 text-text-tertiary" />
            <div>
              <p className="text-xs text-text-tertiary">Last Backup</p>
              <p className="text-sm font-medium text-text-secondary">
                {project.lastBackup
                  ? formatDistanceToNow(new Date(project.lastBackup), { addSuffix: true })
                  : 'Never'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <DocumentTextIcon className="w-4 h-4 text-text-tertiary" />
            <div>
              <p className="text-xs text-text-tertiary">Files</p>
              <p className="text-sm font-medium text-text-secondary">
                {project.fileCount.toLocaleString()}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <ArrowPathIcon className="w-4 h-4 text-text-tertiary" />
            <div>
              <p className="text-xs text-text-tertiary">Backups</p>
              <p className="text-sm font-medium text-text-secondary">
                {project.backupCount}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <ChartBarIcon className="w-4 h-4 text-text-tertiary" />
            <div>
              <p className="text-xs text-text-tertiary">Size</p>
              <p className="text-sm font-medium text-text-secondary">
                {formatSize(project.size)}
              </p>
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mb-4">
          <div className="flex justify-between text-xs text-text-tertiary mb-1">
            <span>Storage Used</span>
            <span>{formatSize(project.size)}</span>
          </div>
          <div className="h-1.5 bg-savior-bg rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: '65%' }}
              transition={{ duration: 1, ease: "easeOut" }}
              className="h-full bg-gradient-to-r from-savior-red to-accent-coral rounded-full"
            />
          </div>
        </div>

        {/* Action Buttons */}
        <AnimatePresence>
          {isHovered && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              className="flex gap-2"
              onClick={(e) => e.stopPropagation()}
            >
              {project.isActive ? (
                <button
                  onClick={() => onAction?.('pause', project.path)}
                  className="flex-1 btn-ghost text-xs py-2"
                >
                  <PauseIcon className="w-4 h-4" />
                  Pause
                </button>
              ) : (
                <button
                  onClick={() => onAction?.('resume', project.path)}
                  className="flex-1 btn-ghost text-xs py-2"
                >
                  <PlayIcon className="w-4 h-4" />
                  Resume
                </button>
              )}

              <button
                onClick={() => onAction?.('stats', project.path)}
                className="flex-1 btn-ghost text-xs py-2"
              >
                <ChartBarIcon className="w-4 h-4" />
                Stats
              </button>

              <button
                onClick={() => onAction?.('delete', project.path)}
                className="btn-ghost text-xs py-2 text-accent-coral hover:bg-accent-coral/20"
              >
                <TrashIcon className="w-4 h-4" />
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Animated border gradient */}
      <motion.div
        className="absolute inset-0 rounded-lg pointer-events-none"
        animate={{
          background: isHovered
            ? 'linear-gradient(45deg, transparent, rgba(239, 62, 54, 0.2), transparent)'
            : 'none'
        }}
        transition={{ duration: 0.3 }}
      />
    </motion.div>
  );
};