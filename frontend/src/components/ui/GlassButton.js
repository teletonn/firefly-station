import React from 'react';
import { motion } from 'framer-motion';

/**
 * Glassmorphism Button component with hover effects and animations
 */
const GlassButton = ({
  children,
  onClick,
  variant = 'primary', // 'primary', 'secondary', 'success', 'danger', 'ghost'
  size = 'md', // 'sm', 'md', 'lg'
  disabled = false,
  loading = false,
  icon,
  className = '',
  glassmorphism = true,
  ...props
}) => {
  const getVariantStyles = () => {
    const variants = {
      primary: 'bg-blue-500/20 hover:bg-blue-500/30 text-blue-100 border-blue-300/30',
      secondary: 'bg-gray-500/20 hover:bg-gray-500/30 text-gray-100 border-gray-300/30',
      success: 'bg-green-500/20 hover:bg-green-500/30 text-green-100 border-green-300/30',
      danger: 'bg-red-500/20 hover:bg-red-500/30 text-red-100 border-red-300/30',
      ghost: 'bg-transparent hover:bg-white/10 text-white border-white/20'
    };
    return variants[variant] || variants.primary;
  };

  const getSizeStyles = () => {
    const sizes = {
      sm: 'px-3 py-1.5 text-sm',
      md: 'px-4 py-2 text-base',
      lg: 'px-6 py-3 text-lg'
    };
    return sizes[size] || sizes.md;
  };

  const baseClasses = `
    ${getVariantStyles()}
    ${getSizeStyles()}
    ${glassmorphism ? 'backdrop-blur-sm' : ''}
    border rounded-lg font-medium
    transition-all duration-200
    focus:outline-none focus:ring-2 focus:ring-white/20
    disabled:opacity-50 disabled:cursor-not-allowed
    flex items-center justify-center space-x-2
    ${className}
  `.trim();

  const content = (
    <>
      {loading ? (
        <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
      ) : (
        <>
          {icon && <span className="flex-shrink-0">{icon}</span>}
          <span>{children}</span>
        </>
      )}
    </>
  );

  if (glassmorphism) {
    return (
      <motion.button
        onClick={disabled || loading ? undefined : onClick}
        className={baseClasses}
        whileHover={!disabled && !loading ? { scale: 1.05 } : {}}
        whileTap={!disabled && !loading ? { scale: 0.95 } : {}}
        disabled={disabled || loading}
        {...props}
      >
        {content}
      </motion.button>
    );
  }

  return (
    <motion.button
      onClick={disabled || loading ? undefined : onClick}
      className={baseClasses}
      whileHover={!disabled && !loading ? { scale: 1.05 } : {}}
      whileTap={!disabled && !loading ? { scale: 0.95 } : {}}
      disabled={disabled || loading}
      {...props}
    >
      {content}
    </motion.button>
  );
};

export default GlassButton;