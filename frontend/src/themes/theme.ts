import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'dark',
    background: {
      paper: '#0f1f2b', // Nav bar bg color
      default: '#091622',
    },
    primary: {
      main: '#091622', // 'Get Started' green button
    },
    text: {
      primary: '#ffffff',
      secondary: '#C8D1E0',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    fontWeightRegular: 400,
    fontWeightMedium: 500,
    fontWeightBold: 600,
  },
});

export default theme;
