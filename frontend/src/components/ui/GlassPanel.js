import React from 'react';
import Glassmorphism from './Glassmorphism';

/**
 * Glassmorphism Panel component for larger content areas
 */
const GlassPanel = ({
  children,
  title,
  subtitle,
  headerActions,
  footer,
  className = '',
  variant = 'default',
  intensity = 'medium',
  size = 'md', // 'sm', 'md', 'lg', 'xl', 'full'
  ...props
}) => {
  const getSizeStyles = () => {
    const sizes = {
      sm: 'max-w-sm',
      md: 'max-w-md',
      lg: 'max-w-lg',
      xl: 'max-w-xl',
      full: 'w-full'
    };
    return sizes[size] || sizes.md;
  };

  return (
    <Glassmorphism
      className={`w-full ${getSizeStyles()} ${className}`}
      variant={variant}
      intensity={intensity}
      {...props}
    >
      {(title || subtitle || headerActions) && (
        <div className="flex items-center justify-between mb-6 pb-4 border-b border-white/10">
          <div>
            {title && (
              <h2 className="text-xl font-bold text-white">
                {title}
              </h2>
            )}
            {subtitle && (
              <p className="text-sm text-gray-300 mt-1">
                {subtitle}
              </p>
            )}
          </div>
          {headerActions && (
            <div className="flex items-center space-x-2">
              {headerActions}
            </div>
          )}
        </div>
      )}

      <div className="flex-1">
        {children}
      </div>

      {footer && (
        <div className="mt-6 pt-4 border-t border-white/10">
          {footer}
        </div>
      )}
    </Glassmorphism>
  );
};

export default GlassPanel;