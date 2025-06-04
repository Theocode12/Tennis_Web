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

  const baseStyles: SxProps<Theme> = {
    textTransform: 'none',
    fontWeight: 600,
    px: 3,
    py: 1.5,
    fontSize: { xs: '0.9rem', sm: '1rem' },
    ...sx
  }

  if (to) {
    return (
      <Button 
        component={RouterLink} 
        to={to} 
        variant={variant} 
        size={size} 
        color={color} 
        onClick={onClick} 
        sx={{...baseStyles}}>
        {label}
      </Button>
    );
  }

  if (href) {
    return (
      <Button 
        component="a" 
        href={href} 
        target="_blank" 
        rel="noopener"
        variant={variant}
        size={size}
        color={color}
        onClick={onClick}
        sx={{...baseStyles}}>
        {label}
      </Button>
    );
  }

  return <Button 
            variant={variant}
            size={size}
            color={color}
            onClick={onClick}
            sx={{...baseStyles}}>
            {label}
          </Button>;
}
