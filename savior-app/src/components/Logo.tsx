import React from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import logoImage from '../assets/logo';

interface LogoProps {
  size?: 'small' | 'medium' | 'large' | 'hero';
  state?: 'default' | 'loading' | 'pulsing' | 'error' | 'success';
  showText?: boolean;
  className?: string;
}

const sizeMap = {
  small: 'w-8 h-8',
  medium: 'w-12 h-12',
  large: 'w-16 h-16',
  hero: 'w-32 h-32',
};

export const Logo: React.FC<LogoProps> = ({
  size = 'medium',
  state = 'default',
  showText = false,
  className = ''
}) => {
  const getAnimationClass = () => {
    switch (state) {
      case 'loading':
        return 'animate-spin-slow';
      case 'pulsing':
        return 'animate-pulse-slow';
      case 'error':
        return 'animate-shake';
      case 'success':
        return 'animate-scale-in';
      default:
        return '';
    }
  };

  const getFilterClass = () => {
    switch (state) {
      case 'error':
        return 'hue-rotate-[20deg] saturate-150';
      case 'success':
        return 'hue-rotate-[-50deg]';
      default:
        return '';
    }
  };

  return (
    <div className={clsx('flex items-center gap-3', className)}>
      <motion.div
        initial={{ scale: 0, rotate: -180 }}
        animate={{ scale: 1, rotate: 0 }}
        transition={{
          type: "spring",
          stiffness: 200,
          damping: 15
        }}
        whileHover={{
          scale: 1.05,
          filter: 'drop-shadow(0 0 20px rgba(239, 62, 54, 0.5))'
        }}
        className="relative"
      >
        <img
          src={logoImage}
          alt="Savior"
          className={clsx(
            sizeMap[size],
            'logo-animated',
            getAnimationClass(),
            getFilterClass(),
            'transition-all duration-300'
          )}
        />

        {/* Glow effect for active state */}
        {state === 'pulsing' && (
          <div className={clsx(
            'absolute inset-0',
            sizeMap[size],
            'bg-savior-red/30 rounded-full blur-xl animate-pulse-slow'
          )} />
        )}

        {/* Success checkmark overlay */}
        {state === 'success' && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: "spring", stiffness: 300 }}
            className="absolute inset-0 flex items-center justify-center"
          >
            <svg
              className="w-1/2 h-1/2 text-accent-green"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={3}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </motion.div>
        )}
      </motion.div>

      {showText && (
        <motion.div
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
        >
          <h1 className={clsx(
            'font-display font-bold',
            size === 'hero' ? 'text-4xl' :
            size === 'large' ? 'text-2xl' :
            size === 'medium' ? 'text-xl' :
            'text-lg'
          )}>
            <span className="text-gradient">Savior</span>
          </h1>
        </motion.div>
      )}
    </div>
  );
};