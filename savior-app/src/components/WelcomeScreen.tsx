import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { Logo } from './Logo';
import {
  SparklesIcon,
  BoltIcon,
  CloudArrowUpIcon,
  ShieldCheckIcon,
  CommandLineIcon,
  ArrowRightIcon
} from '@heroicons/react/24/outline';

interface WelcomeScreenProps {
  onGetStarted: () => void;
}

export const WelcomeScreen: React.FC<WelcomeScreenProps> = ({ onGetStarted }) => {
  const [hoveredFeature, setHoveredFeature] = useState<number | null>(null);

  const features = [
    {
      icon: ShieldCheckIcon,
      title: 'Guardian Mode',
      description: 'Silently watching, always protecting',
      color: 'from-savior-red to-savior-red-dark',
      glow: 'rgba(255, 85, 85, 0.3)'
    },
    {
      icon: BoltIcon,
      title: 'Instant Recovery',
      description: 'When disaster strikes at 3am',
      color: 'from-accent-gold to-savior-red',
      glow: 'rgba(255, 181, 85, 0.3)'
    },
    {
      icon: SparklesIcon,
      title: 'Smart & Silent',
      description: 'Never interrupts your flow',
      color: 'from-accent-purple to-accent-blue',
      glow: 'rgba(153, 85, 255, 0.3)'
    },
    {
      icon: CloudArrowUpIcon,
      title: 'Cloud Safety',
      description: 'Your code, everywhere, always',
      color: 'from-accent-blue to-accent-green',
      glow: 'rgba(85, 153, 255, 0.3)'
    }
  ];

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: {
        type: "spring" as const,
        stiffness: 100
      }
    }
  };

  return (
    <div className="min-h-screen bg-savior-bg flex items-center justify-center p-8 overflow-hidden relative">
      {/* Animated background gradient */}
      <div className="absolute inset-0">
        <div className="absolute inset-0 bg-gradient-to-br from-savior-red/3 via-transparent to-accent-purple/3" />
        <motion.div
          className="absolute -top-40 -right-40 w-96 h-96 rounded-full blur-3xl"
          style={{ background: 'radial-gradient(circle, rgba(255, 85, 85, 0.15), transparent)' }}
          animate={{
            x: [0, 50, 0],
            y: [0, -50, 0],
          }}
          transition={{
            duration: 20,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        <motion.div
          className="absolute -bottom-40 -left-40 w-96 h-96 rounded-full blur-3xl"
          style={{ background: 'radial-gradient(circle, rgba(153, 85, 255, 0.1), transparent)' }}
          animate={{
            x: [0, -50, 0],
            y: [0, 50, 0],
          }}
          transition={{
            duration: 25,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
      </div>

      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="max-w-5xl w-full relative z-10"
      >
        {/* Logo and Title */}
        <motion.div
          variants={itemVariants}
          className="text-center mb-12"
        >
          <div className="flex justify-center mb-6">
            <Logo size="hero" state="default" />
          </div>

          <motion.h1
            className="text-6xl font-display font-bold mb-4"
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
          >
            <span className="text-gradient">Savior</span>
          </motion.h1>

          <motion.p
            variants={itemVariants}
            className="text-xl text-text-secondary mb-2"
          >
            Your Code's Guardian Angel
          </motion.p>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }}
            className="text-sm text-text-tertiary italic"
          >
            "Because every developer breaks things at 3am"
          </motion.p>
        </motion.div>

        {/* Quick Start Terminal */}
        <motion.div
          variants={itemVariants}
          className="glass-card p-6 mb-12"
        >
          <div className="flex items-center gap-2 mb-4">
            <CommandLineIcon className="w-5 h-5 text-savior-red" />
            <span className="text-sm font-mono text-text-secondary">Terminal</span>
          </div>

          <div className="code-block space-y-3">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.5 }}
            >
              <span className="syntax-comment"># Install Savior</span>
              <div className="text-text-primary">
                <span className="syntax-keyword">pip</span> install savior
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.7 }}
            >
              <span className="syntax-comment"># Start protecting your work</span>
              <div className="text-text-primary">
                <span className="syntax-keyword">cd</span> my-project
              </div>
              <div className="text-text-primary">
                <span className="syntax-keyword">savior</span> watch
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.9 }}
              className="relative"
            >
              <span className="syntax-comment"># That's it. You're protected. 🛟</span>
              <motion.span
                className="absolute -right-8 text-2xl"
                animate={{ rotate: [0, 10, -10, 0] }}
                transition={{ duration: 2, repeat: Infinity, delay: 1 }}
              >
                ✨
              </motion.span>
            </motion.div>
          </div>
        </motion.div>

        {/* Features Grid */}
        <motion.div
          variants={itemVariants}
          className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12"
        >
          {features.map((feature, index) => {
            const Icon = feature.icon;
            return (
              <motion.div
                key={index}
                whileHover={{ scale: 1.05, y: -5 }}
                onHoverStart={() => setHoveredFeature(index)}
                onHoverEnd={() => setHoveredFeature(null)}
                className="glass-card p-4 cursor-pointer group"
              >
                <motion.div
                  className={clsx(
                    'w-10 h-10 rounded-lg flex items-center justify-center mb-3 relative',
                    'bg-gradient-to-br',
                    feature.color
                  )}
                  animate={hoveredFeature === index ? {
                    rotate: 5,
                    scale: 1.1
                  } : {
                    rotate: 0,
                    scale: 1
                  }}
                  transition={{ duration: 0.5 }}
                  style={{
                    boxShadow: hoveredFeature === index ? `0 0 20px ${feature.glow}` : 'none'
                  }}
                >
                  <Icon className="w-5 h-5 text-white" />
                </motion.div>

                <h3 className="font-semibold text-text-primary mb-1 text-sm">
                  {feature.title}
                </h3>
                <p className="text-xs text-text-tertiary leading-relaxed">
                  {feature.description}
                </p>

                <AnimatePresence>
                  {hoveredFeature === index && (
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: '100%' }}
                      exit={{ width: 0 }}
                      className={clsx(
                        'h-0.5 mt-3 rounded-full',
                        'bg-gradient-to-r',
                        feature.color
                      )}
                    />
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </motion.div>

        {/* CTA Section */}
        <motion.div
          variants={itemVariants}
          className="text-center"
        >
          <motion.button
            onClick={onGetStarted}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="btn-primary text-lg px-10 py-4 group relative overflow-hidden"
          >
            <span className="relative z-10">Start Protecting My Work</span>
            <motion.div
              className="inline-block ml-2 relative z-10"
              animate={{ x: [0, 5, 0] }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                ease: "easeInOut"
              }}
            >
              <ArrowRightIcon className="w-5 h-5" />
            </motion.div>
            <motion.div
              className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
              initial={{ x: '-100%' }}
              whileHover={{ x: '100%' }}
              transition={{ duration: 0.6 }}
            />
          </motion.button>

          <motion.p
            variants={itemVariants}
            className="text-sm text-text-tertiary mt-6"
          >
            <span className="text-text-secondary font-medium">"The best backup is the one you don't have to think about"</span>
          </motion.p>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.5 }}
            className="mt-8 space-y-2"
          >
            <p className="text-xs text-text-tertiary">
              Join thousands of developers who sleep better at night
            </p>
            <p className="text-xs text-text-tertiary">
              Made with <motion.span
                className="text-savior-red inline-block"
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
              >❤️</motion.span> for developers who break things
            </p>
          </motion.div>
        </motion.div>
      </motion.div>
    </div>
  );
};