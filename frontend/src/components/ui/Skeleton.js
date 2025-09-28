import React from 'react';

const Skeleton = ({
  className = '',
  variant = 'default',
  animated = true,
  ...props
}) => {
  const baseClasses = 'bg-gray-700/50 rounded';

  const variantClasses = {
    default: '',
    text: 'h-4',
    title: 'h-6',
    avatar: 'h-10 w-10 rounded-full',
    button: 'h-10 w-20',
    card: 'h-32',
    image: 'h-48 w-full'
  };

  const animationClasses = animated
    ? 'animate-pulse'
    : '';

  return (
    <div
      className={`${baseClasses} ${variantClasses[variant] || ''} ${animationClasses} ${className}`}
      {...props}
      aria-hidden="true"
    />
  );
};

// Skeleton components for common patterns
export const SkeletonText = ({ lines = 1, className = '' }) => (
  <div className={`space-y-2 ${className}`}>
    {Array.from({ length: lines }, (_, i) => (
      <Skeleton
        key={i}
        variant="text"
        className={i === lines - 1 && lines > 1 ? 'w-3/4' : 'w-full'}
      />
    ))}
  </div>
);

export const SkeletonCard = ({ className = '' }) => (
  <div className={`p-6 space-y-4 ${className}`}>
    <Skeleton variant="title" className="w-1/2" />
    <SkeletonText lines={3} />
    <div className="flex space-x-2">
      <Skeleton variant="button" />
      <Skeleton variant="button" />
    </div>
  </div>
);

export const SkeletonTable = ({ rows = 5, columns = 4, className = '' }) => (
  <div className={`space-y-3 ${className}`}>
    {/* Header */}
    <div className="flex space-x-4">
      {Array.from({ length: columns }, (_, i) => (
        <Skeleton key={`header-${i}`} variant="text" className="flex-1" />
      ))}
    </div>
    {/* Rows */}
    {Array.from({ length: rows }, (_, rowIndex) => (
      <div key={`row-${rowIndex}`} className="flex space-x-4">
        {Array.from({ length: columns }, (_, colIndex) => (
          <Skeleton
            key={`cell-${rowIndex}-${colIndex}`}
            variant="text"
            className="flex-1"
          />
        ))}
      </div>
    ))}
  </div>
);

export const SkeletonList = ({ items = 3, className = '' }) => (
  <div className={`space-y-4 ${className}`}>
    {Array.from({ length: items }, (_, i) => (
      <div key={i} className="flex items-center space-x-4">
        <Skeleton variant="avatar" />
        <div className="flex-1 space-y-2">
          <Skeleton variant="text" className="w-1/2" />
          <Skeleton variant="text" className="w-3/4" />
        </div>
      </div>
    ))}
  </div>
);

export default Skeleton;