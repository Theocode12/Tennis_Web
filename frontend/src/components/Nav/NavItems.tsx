// components/Nav/NavItems.jsx
import { Box } from '@mui/material';
import NavItem from './NavItem';

const navLinks = [
  { label: 'Home', path: '/' },
  { label: 'About', path: '/about' },
  { label: 'Create Match', path: '/create' },
  { label: 'Live Games', path: '/live' },
  { label: 'FAQ', path: '/faq' },
];

export default function NavItems() {
  return (
    <Box sx={{ display: 'flex', gap: 3 }}>
      {navLinks.map(({ label, path }) => (
        <NavItem key={label} label={label} path={path} />
      ))}
    </Box>
  );
}

