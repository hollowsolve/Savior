import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import {
  FolderIcon,
  ClockIcon,
  Cog6ToothIcon,
  CloudIcon,
  ChartBarIcon,
  CommandLineIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ArrowDownTrayIcon,
  ShieldCheckIcon
} from '@heroicons/react/24/outline';
import { Logo } from './Logo';

interface SidebarProps {
  currentView: string;
  onNavigate: (view: 'projects' | 'backups' | 'settings' | 'timeline' | 'cloud') => void;
  projectCount: number;
  isCollapsed: boolean;
  onCollapseToggle: (collapsed: boolean) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentView, onNavigate, projectCount, isCollapsed, onCollapseToggle }) => {
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);

  const menuItems = [
    {
      id: 'projects',
      label: 'Projects',
      icon: FolderIcon,
      badge: projectCount > 0 ? projectCount : null,
      color: 'text-info'
    },
    {
      id: 'timeline',
      label: 'Timeline',
      icon: ClockIcon,
      color: 'text-accent-purple'
    },
    {
      id: 'cloud',
      label: 'Cloud Sync',
      icon: CloudIcon,
      color: 'text-success'
    },
    {
      id: 'settings',
      label: 'Settings',
      icon: Cog6ToothIcon,
      color: 'text-text-tertiary'
    }
  ];

  const bottomTools = [
    {
      id: 'stats',
      label: 'Statistics',
      icon: ChartBarIcon,
      onClick: () => console.log('Statistics')
    },
    {
      id: 'cli',
      label: 'Open CLI',
      icon: CommandLineIcon,
      onClick: () => console.log('Open CLI')
    }
  ];

  return (
    <motion.aside
      initial={{ x: -100, opacity: 0 }}
      animate={{
        x: 0,
        opacity: 1,
        width: isCollapsed ? 80 : 240
      }}
      transition={{ type: "spring", stiffness: 200, damping: 20 }}
      className={clsx(
        'relative flex flex-col',
        'glass-card border-r border-savior-border/30',
        'transition-all duration-300 backdrop-blur-xl'
      )}
    >
      {/* Header with Logo */}
      <div className={clsx(
        'p-4 border-b border-savior-border/50',
        'flex items-center',
        isCollapsed ? 'justify-center' : 'justify-between'
      )}>
        <Logo
          size={isCollapsed ? 'medium' : 'large'}
          showText={!isCollapsed}
          state={projectCount > 0 ? 'pulsing' : 'default'}
        />

        {!isCollapsed && (
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={() => onCollapseToggle(!isCollapsed)}
            className="p-1.5 rounded-lg hover:bg-savior-surface-2 transition-colors"
          >
            <ChevronLeftIcon className="w-4 h-4 text-text-tertiary" />
          </motion.button>
        )}
      </div>

      {/* Expand button when collapsed */}
      {isCollapsed && (
        <motion.button
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => onCollapseToggle(false)}
          className="absolute top-4 right-2 p-1.5 rounded-lg hover:bg-savior-surface-2 transition-colors z-10"
        >
          <ChevronRightIcon className="w-4 h-4 text-text-tertiary" />
        </motion.button>
      )}

      {/* Main Navigation */}
      <nav className="flex-1 p-3 space-y-1 custom-scrollbar overflow-y-auto">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentView === item.id;

          return (
            <motion.button
              key={item.id}
              onClick={() => onNavigate(item.id as any)}
              onMouseEnter={() => setHoveredItem(item.id)}
              onMouseLeave={() => setHoveredItem(null)}
              whileHover={{ x: 2 }}
              whileTap={{ scale: 0.98 }}
              className={clsx(
                'sidebar-item w-full',
                isActive && 'active',
                'relative group'
              )}
            >
              <motion.div
                animate={{
                  rotate: hoveredItem === item.id ? 10 : 0,
                  scale: hoveredItem === item.id ? 1.2 : 1
                }}
                transition={{ duration: 0.5, type: "spring", stiffness: 300 }}
                className="relative"
              >
                <Icon className={clsx(
                  'w-5 h-5 transition-all duration-300',
                  isActive ? 'text-savior-red neon-glow' : item.color,
                  hoveredItem === item.id && 'filter drop-shadow(0 0 8px currentColor)'
                )} />
              </motion.div>

              <AnimatePresence>
                {!isCollapsed && (
                  <motion.span
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -10 }}
                    className="font-medium"
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>

              {item.badge && (
                <motion.span
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className={clsx(
                    'absolute',
                    isCollapsed ? 'top-0 right-0' : 'right-3',
                    'badge badge-info'
                  )}
                >
                  {item.badge}
                </motion.span>
              )}

              {/* Tooltip for collapsed state */}
              {isCollapsed && (
                <div className="tooltip" data-tooltip={item.label} />
              )}
            </motion.button>
          );
        })}
      </nav>

      {/* Bottom Section */}
      <div className="p-3 border-t border-savior-border/50 space-y-1">
        {/* Backup Status */}
        <motion.div
          whileHover={{ scale: 1.05 }}
          className={clsx(
            'p-3 rounded-lg glass-card bg-gradient-to-br from-green-500/10 to-green-600/5',
            'flex items-center gap-3 cursor-pointer',
            isCollapsed && 'justify-center'
          )}
        >
          <div className="relative">
            <ShieldCheckIcon className="w-5 h-5 text-accent-green neon-glow" />
            <motion.span
              className="absolute -bottom-1 -right-1 w-2 h-2 bg-accent-green rounded-full"
              animate={{ scale: [1, 1.5, 1], opacity: [1, 0.5, 1] }}
              transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
            />
          </div>
          {!isCollapsed && (
            <div className="flex-1">
              <p className="text-xs text-text-tertiary">Status</p>
              <p className="text-sm font-medium text-accent-green">Protected</p>
            </div>
          )}
        </motion.div>

        {/* Bottom Tools */}
        {bottomTools.map((tool) => {
          const Icon = tool.icon;

          return (
            <motion.button
              key={tool.id}
              onClick={tool.onClick}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className={clsx(
                'w-full btn-ghost',
                'flex items-center',
                isCollapsed ? 'justify-center' : 'justify-start gap-3'
              )}
              title={isCollapsed ? tool.label : undefined}
            >
              <Icon className="w-5 h-5" />
              {!isCollapsed && (
                <span className="text-sm">{tool.label}</span>
              )}
            </motion.button>
          );
        })}

        {/* Download Update (when available) */}
        {false && ( // Replace with actual update check
          <motion.button
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full btn-primary text-sm"
          >
            <ArrowDownTrayIcon className="w-4 h-4" />
            {!isCollapsed && <span>Update Available</span>}
          </motion.button>
        )}
      </div>

      {/* Decorative gradient line */}
      <motion.div
        className="absolute bottom-0 left-0 right-0 h-px"
        style={{
          background: 'linear-gradient(90deg, transparent, var(--color-savior-red), transparent)',
        }}
        animate={{
          backgroundPosition: ['0% 50%', '100% 50%', '0% 50%'],
        }}
        transition={{
          duration: 4,
          repeat: Infinity,
          ease: "linear"
        }}
      />
    </motion.aside>
  );
};