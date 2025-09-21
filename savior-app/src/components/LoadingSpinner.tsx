import React from 'react';
import { motion } from 'framer-motion';

interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large';
  message?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ size = 'medium', message }) => {
  const sizeMap = {
    small: 24,
    medium: 48,
    large: 64
  };

  const circleSize = sizeMap[size];

  return (
    <div className="flex flex-col items-center justify-center gap-4">
      <div className="relative" style={{ width: circleSize, height: circleSize }}>
        {/* Outer ring */}
        <motion.div
          className="absolute inset-0 rounded-full"
          style={{
            background: 'conic-gradient(from 0deg, transparent, var(--color-savior-red), transparent)',
            filter: 'blur(8px)'
          }}
          animate={{ rotate: 360 }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "linear"
          }}
        />

        {/* Inner ring */}
        <motion.div
          className="absolute inset-2 rounded-full"
          style={{
            background: 'conic-gradient(from 180deg, transparent, var(--color-accent-purple), transparent)',
          }}
          animate={{ rotate: -360 }}
          transition={{
            duration: 3,
            repeat: Infinity,
            ease: "linear"
          }}
        />

        {/* Center dot */}
        <motion.div
          className="absolute inset-0 flex items-center justify-center"
          animate={{ scale: [1, 1.2, 1] }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        >
          <div
            className="rounded-full bg-gradient-to-br from-savior-red to-accent-purple"
            style={{ width: circleSize * 0.3, height: circleSize * 0.3 }}
          />
        </motion.div>
      </div>

      {message && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-text-secondary text-sm font-medium"
        >
          {message}
        </motion.p>
      )}
    </div>
  );
};

export const SkeletonLoader: React.FC<{ className?: string }> = ({ className = '' }) => {
  return (
    <div className={`relative overflow-hidden bg-gray-800/50 rounded-lg ${className}`}>
      <div className="shimmer absolute inset-0" />
    </div>
  );
};

export const PulseLoader: React.FC = () => {
  return (
    <div className="flex space-x-2">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="w-3 h-3 bg-gradient-to-br from-savior-red to-accent-purple rounded-full"
          animate={{
            scale: [1, 1.5, 1],
            opacity: [0.5, 1, 0.5]
          }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            delay: i * 0.2,
            ease: "easeInOut"
          }}
        />
      ))}
    </div>
  );
};