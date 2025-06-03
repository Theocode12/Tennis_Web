import { Typography } from "@mui/material";

export default function NavTitle() {
  return (
    <Typography sx={{ 
      fontWeight: "bold", 
      fontSize: { xs: '0.9rem', sm: '1rem', md: '1.5rem' } 
      }} variant="h6">
        Tennis Simulator
    </Typography>
  )
}