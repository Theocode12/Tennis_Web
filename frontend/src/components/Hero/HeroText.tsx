import { Box, Typography, Stack } from '@mui/material';
import CTAButton from './CTAButton';



export default function HeroText() {
  return (
    <Box
      sx={{
        flex: 1,
        px: 4,
        py: 6,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
      }}
    >
      <Typography
        variant="h3"
        fontWeight={700}
        gutterBottom
        sx={{
          fontSize: { xs: '2rem', sm: '3rem', md: '3.5rem' },
        }}
      >
        Experience Tennis Like Never Before
      </Typography>

      <Typography
        variant="subtitle1"
        color="text.secondary"
        sx={{ maxWidth: '500px', mb: 4 }}
      >
        Create matches, spectate live games, or challenge AI opponents — all in real-time.
      </Typography>

      <Stack direction="row" spacing={2}>
        /** background = #a2a8ae color=black */
        <CTAButton label='Get Started' />
         /** background = #000000 color=white */
        <CTAButton label='Learn More' variant='outlined' />
      </Stack>
    </Box>
  );
}
