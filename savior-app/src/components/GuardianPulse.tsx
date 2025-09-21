import React from 'react';
import { motion } from 'framer-motion';

interface GuardianPulseProps {
  isActive?: boolean;
  size?: 'small' | 'medium' | 'large';
  color?: string;
}

export const GuardianPulse: React.FC<GuardianPulseProps> = ({
  isActive = true,
  size = 'medium',
  color = 'var(--color-savior-red)'
}) => {
  const sizeMap = {
    small: { base: 8, rings: [16, 24, 32] },
    medium: { base: 12, rings: [24, 36, 48] },
    large: { base: 16, rings: [32, 48, 64] }
  };

  const dimensions = sizeMap[size];

  if (!isActive) {
    return (
      <div
        className="rounded-full opacity-30"
        style={{
          width: dimensions.base,
          height: dimensions.base,
          backgroundColor: color
        }}
      />
    );
  }

  return (
    <div className="relative flex items-center justify-center">
      {/* Outer rings */}
      {dimensions.rings.map((ringSize, index) => (
        <motion.div
          key={index}
          className="absolute rounded-full"
          style={{
            width: ringSize,
            height: ringSize,
            border: `1px solid ${color}`,
            opacity: 0.3 - (index * 0.1)
          }}
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.3 - (index * 0.1), 0, 0.3 - (index * 0.1)]
          }}
          transition={{
            duration: 3,
            repeat: Infinity,
            delay: index * 0.5,
            ease: "easeOut"
          }}
        />
      ))}

      {/* Core */}
      <motion.div
        className="relative rounded-full"
        style={{
          width: dimensions.base,
          height: dimensions.base,
          background: `radial-gradient(circle, ${color}, ${color}88)`,
          boxShadow: `0 0 20px ${color}66`
        }}
        animate={{
          scale: [1, 1.1, 1],
          boxShadow: [
            `0 0 20px ${color}66`,
            `0 0 30px ${color}99`,
            `0 0 20px ${color}66`
          ]
        }}
        transition={{
          duration: 2,
          repeat: Infinity,
          ease: "easeInOut"
        }}
      />

      {/* Inner light */}
      <motion.div
        className="absolute rounded-full"
        style={{
          width: dimensions.base * 0.4,
          height: dimensions.base * 0.4,
          background: 'white',
          opacity: 0.8
        }}
        animate={{
          opacity: [0.8, 0.4, 0.8]
        }}
        transition={{
          duration: 2,
          repeat: Infinity,
          ease: "easeInOut"
        }}
      />
    </div>
  );
};

export const GuardianShield: React.FC<{ className?: string }> = ({ className = "" }) => {
  return (
    <motion.svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      animate={{
        filter: [
          "drop-shadow(0 0 0px rgba(255, 68, 68, 0))",
          "drop-shadow(0 0 10px rgba(255, 68, 68, 0.5))",
          "drop-shadow(0 0 0px rgba(255, 68, 68, 0))"
        ]
      }}
      transition={{
        duration: 2,
        repeat: Infinity,
        ease: "easeInOut"
      }}
    >
      <motion.path
        d="M12 2L4 7V12C4 16.55 6.84 20.74 11 22C15.16 20.74 20 16.55 20 12V7L12 2Z"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 2, ease: "easeInOut" }}
      />
      <motion.path
        d="M9 12L11 14L15 10"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ delay: 0.5, duration: 1, ease: "easeOut" }}
      />
    </motion.svg>
  );
};