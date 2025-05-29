import { Box } from '@mui/material';
import NavContent from './NavContent';

export default function Nav() {
  return (
    <Box sx={{ width: '100%', bgcolor: 'background.paper', boxShadow: 1 }}>
      <NavContent />
    </Box>
  );
}
