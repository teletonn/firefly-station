import React from 'react';
import { motion } from 'framer-motion';

/**
 * Glassmorphism component with backdrop blur effects
 * Provides a modern frosted glass appearance with mobile-first design
 */
const Glassmorphism = ({
  children,
  className = '',
  variant = 'default', // 'default', 'subtle', 'strong', 'dark'
  intensity = 'medium', // 'light', 'medium', 'strong'
  animated = true,
  hover = true,
  border = true,
  rounded = 'lg',
  padding = 'p-4 md:p-6', // Mobile-first padding
  touchable = false, // For touch interactions
  ...props
}) => {
  const getVariantStyles = () => {
    const variants = {
      default: 'glass-effect',
      subtle: 'bg-glass-50 backdrop-blur-xs',
      strong: 'bg-glass-200 backdrop-blur-lg',
      dark: 'bg-gray-900/20 backdrop-blur-md'
    };
    return variants[variant] || variants.default;
  };

  const getIntensityStyles = () => {
    const intensities = {
      light: 'shadow-glass',
      medium: 'shadow-glass border-white/20',
      strong: 'shadow-glass-lg border-white/30'
    };
    return intensities[intensity] || intensities.medium;
  };

  const getRoundedStyles = () => {
    const roundedStyles = {
      none: 'rounded-none',
      sm: 'rounded-sm',
      md: 'rounded-md',
      lg: 'rounded-lg',
      xl: 'rounded-xl',
      '2xl': 'rounded-2xl',
      '3xl': 'rounded-3xl',
      full: 'rounded-full'
    };
    return roundedStyles[rounded] || roundedStyles.lg;
  };

  const baseClasses = `
    ${getVariantStyles()}
    ${getIntensityStyles()}
    ${getRoundedStyles()}
    ${padding}
    ${border ? 'border' : ''}
    ${touchable ? 'touch-manipulation active:scale-95 transition-transform' : ''}
    ${className}
  `.trim();

  const content = (
    <div className={baseClasses} {...props}>
      {children}
    </div>
  );

  if (!animated) return content;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      whileHover={hover && window.innerWidth >= 768 ? {
        scale: 1.02,
        boxShadow: intensity === 'strong' ? '0 25px 50px -12px rgba(0, 0, 0, 0.25)' : '0 20px 25px -5px rgba(0, 0, 0, 0.1)'
      } : {}}
      whileTap={touchable ? { scale: 0.98 } : {}}
      className={`transition-all duration-300 ${hover && window.innerWidth >= 768 ? 'hover:shadow-2xl' : ''}`}
    >
      {content}
    </motion.div>
  );
};

export default Glassmorphism;