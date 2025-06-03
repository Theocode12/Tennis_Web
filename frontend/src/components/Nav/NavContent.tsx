import { Box, IconButton, Drawer, useMediaQuery } from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import { useState } from "react";
import NavTitle from "./NavTitle";
import NavItems from "./NavItems";

export default function NavContent() {
  const isMobile = useMediaQuery("(max-width: 760px)");
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <Box
      sx={{
        maxWidth: "1200px",
        mx: "auto",
        px: 3,
        py: 2,
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
      }}
    >
      <NavTitle />

      {isMobile ? (
        <>
          <IconButton
            edge="end"
            color="inherit"
            onClick={() => setDrawerOpen(true)}
          >
            <MenuIcon />
          </IconButton>

          <Drawer
            anchor="right"
            open={drawerOpen}
            onClose={() => setDrawerOpen(false)}
          >
            <Box
              sx={{
                width: 250,
                display: "flex",
                flexDirection: "column",
                p: 2,
                gap: 2,
              }}
              onClick={() => setDrawerOpen(false)}
            >
              <NavItems direction="column" />
            </Box>
          </Drawer>
        </>
      ) : (
        <NavItems direction="row" />
      )}
    </Box>
  );
}
