import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router";
import './index.css'
import App from './App.tsx'
import { CssBaseline, ThemeProvider } from "@mui/material";
import theme from "./themes/theme.ts";

const root = document.getElementById("root");

if (root) {
  ReactDOM.createRoot(root).render(
    <BrowserRouter>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <App />
      </ThemeProvider>
    </BrowserRouter>
  );
} else {
  console.error("Root element not found!");
}
