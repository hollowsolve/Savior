import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  ServerIcon,
  WifiIcon,
  SignalIcon,
  ShieldCheckIcon,
  HeartIcon
} from '@heroicons/react/24/outline';
import { GuardianPulse } from './GuardianPulse';

export const StatusBar: React.FC = () => {
  const [daemonStatus, setDaemonStatus] = useState<any>(null);
  const [isConnected, setIsConnected] = useState(true);
  const [activity, setActivity] = useState<string>('');

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const status = await window.saviorAPI.getDaemonStatus();
        setDaemonStatus(status);
        setIsConnected(true);
      } catch (error) {
        setIsConnected(false);
      }
    };

    checkStatus();
    const interval = setInterval(checkStatus, 10000); // Check every 10 seconds

    // Subscribe to backup events for activity display
    const unsubBackupStarted = window.saviorAPI.on('backup-started', (data: any) => {
      setActivity('🛟 Guardian is saving your work...');
      setTimeout(() => setActivity(''), 5000);
    });

    const unsubBackupCompleted = window.saviorAPI.on('backup-completed', (data: any) => {
      setActivity('✨ Your code is safe');
      setTimeout(() => setActivity(''), 3000);
    });

    return () => {
      clearInterval(interval);
      unsubBackupStarted();
      unsubBackupCompleted();
    };
  }, []);

  const motivationalMessages = [
    "Your guardian never sleeps 🌙",
    "Code with confidence 💪",
    "We've got your back 🛟",
    "Every save is a promise kept ✨",
    "Protected by Savior ❤️"
  ];

  const [currentMessage] = useState(
    motivationalMessages[Math.floor(Math.random() * motivationalMessages.length)]
  );

  return (
    <footer className="glass-card border-t border-savior-border/30 px-6 py-3">
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-6">
          {/* Guardian Status */}
          <div className="flex items-center gap-2">
            <GuardianPulse size="small" isActive={isConnected} />
            <span className="text-text-secondary">
              {isConnected ? 'Guardian Active' : 'Guardian Sleeping'}
            </span>
          </div>

          {/* Protection Status */}
          {daemonStatus && (
            <motion.div
              className="flex items-center gap-2"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <ShieldCheckIcon className={`w-4 h-4 ${daemonStatus.running ? 'text-green-400 neon-glow' : 'text-text-tertiary'}`} />
              <span className="text-text-secondary">
                {daemonStatus.running ? (
                  <span className="text-green-400">🔒 Protected</span>
                ) : (
                  <span className="text-text-tertiary">Unprotected</span>
                )}
              </span>
            </motion.div>
          )}

          {/* Activity Indicator */}
          <AnimatePresence>
            {activity && (
              <motion.div
                className="flex items-center gap-2"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
              >
                <ArrowPathIcon className="w-4 h-4 animate-spin text-savior-red" />
                <span className="text-text-primary font-medium">{activity}</span>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Right side status */}
        <div className="flex items-center gap-4">
          {/* Motivational message */}
          <motion.div
            className="text-text-tertiary italic text-xs"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1 }}
          >
            {currentMessage}
          </motion.div>

          <div className="flex items-center gap-2">
            <motion.div
              animate={{ scale: [1, 1.1, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              <HeartIcon className="w-4 h-4 text-savior-red" />
            </motion.div>
            <span className="text-text-tertiary text-xs">by Noah Edery</span>
          </div>
        </div>
      </div>
    </footer>
  );
};