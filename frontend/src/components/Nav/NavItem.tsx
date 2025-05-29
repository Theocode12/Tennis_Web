// components/Nav/NavItem.tsx
import { Button } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';

// Define types for the props
interface NavItemProps {
  label: string;
  path: string;
}

export default function NavItem({ label, path }: NavItemProps) {
  return (
    <Button
      component={RouterLink}
      to={path}
      variant="text"
      color="inherit"
      sx={{ textTransform: 'none' }}
    >
      {label}
    </Button>
  );
}
