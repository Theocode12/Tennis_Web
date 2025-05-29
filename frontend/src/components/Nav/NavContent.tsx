import { Box } from '@mui/material';
import NavTitle from './NavTitle';
import NavItems from './NavItems';

export default function NavContent() {
  return (
    <Box
      sx={{
        maxWidth: '1200px',
        mx: 'auto',
        px: 3,
        py: 2,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}
    >
      <NavTitle />
      <NavItems />
    </Box>
  );
}
