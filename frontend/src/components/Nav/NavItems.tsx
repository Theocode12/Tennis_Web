import { Box } from '@mui/material';
import NavItem from './NavItem';

const navLinks = [
  { label: 'Home', path: '/' },
  { label: 'About', path: '/about' },
  { label: 'Create Match', path: '/create' },
  { label: 'Live Games', path: '/live' },
  { label: 'FAQ', path: '/faq' },
];

interface NavItemsProps {
  direction?: "row" | "column";
}

export default function NavItems({ direction = "row" }: NavItemsProps) {
  return (
    <Box
      sx={{
        display: 'flex',
        gap: { xs: 1, sm: 2, md: 3 },
        flexDirection: direction,
      }}
    >
      {navLinks.map(({ label, path }) => (
        <NavItem
          key={label}
          label={label}
          path={path}
          sx={{
            px: { xs: 1, sm: 1.5, md: 2 }, // Padding x-axis
            py: { xs: 0.5, sm: 1 },
            
            fontSize: { xs: '0.75rem', sm: '0.9rem', md: '1rem' },
          }}
        />
      ))}
    </Box>
  );
}
