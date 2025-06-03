// components/CTAButton.tsx
import { Button } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import type { SxProps, Theme } from '@mui/system';

interface CTAButtonProps {
  label: string;
  variant?: 'contained' | 'outlined' | 'text';
  onClick?: () => void;
  to?: string;          // for internal routing
  href?: string;        // for external links
  sx?: SxProps<Theme>;  // for custom styles
  size?: 'small' | 'medium' | 'large';
  color?: 'primary' | 'secondary' | 'success' | 'inherit';
}

export default function CTAButton({
  label,
  variant = 'contained',
  size = 'large',
  color = 'primary',
  onClick,
  to,
  href,
  sx = {},
}: CTAButtonProps) {
  const commonProps = {
    variant,
    size,
    color,
    onClick,
    sx: {
      textTransform: 'none',
      fontWeight: 600,
      px: 3,
      py: 1.5,
      fontSize: { xs: '0.9rem', sm: '1rem' },
      ...sx,
    },
  };

  if (to) {
    return (
      <Button component={RouterLink} to={to} {...commonProps}>
        {label}
      </Button>
    );
  }

//   if (href) {
//     return (
//       <Button href={href} target="_blank" rel="noopener" {...commonProps}>
//         {label}
//       </Button>
//     );
//   }

//   return <Button {...commonProps}>{label}</Button>;
}
