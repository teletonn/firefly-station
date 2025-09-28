import React from 'react';
import Glassmorphism from './Glassmorphism';

/**
 * Glassmorphism Card component for displaying content in glassmorphic containers
 */
const GlassCard = ({
  children,
  title,
  subtitle,
  icon,
  actions,
  className = '',
  variant = 'default',
  intensity = 'medium',
  ...props
}) => {
  return (
    <Glassmorphism
      className={`w-full ${className}`}
      variant={variant}
      intensity={intensity}
      {...props}
    >
      {(title || subtitle || icon) && (
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            {icon && (
              <div className="flex-shrink-0">
                {icon}
              </div>
            )}
            <div>
              {title && (
                <h3 className="text-lg font-semibold text-white">
                  {title}
                </h3>
              )}
              {subtitle && (
                <p className="text-sm text-gray-300">
                  {subtitle}
                </p>
              )}
            </div>
          </div>
          {actions && (
            <div className="flex items-center space-x-2">
              {actions}
            </div>
          )}
        </div>
      )}
      <div className="text-gray-100">
        {children}
      </div>
    </Glassmorphism>
  );
};

export default GlassCard;