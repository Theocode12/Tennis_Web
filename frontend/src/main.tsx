import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router";
import './index.css'
import App from './App.tsx'


const root = document.getElementById("root");

if (root) {
  ReactDOM.createRoot(root).render(
    <BrowserRouter>
      <App />
    </BrowserRouter>
  );
} else {
  console.error("Root element not found!");
}
