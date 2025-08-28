import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./index.css";

// Filter out browser extension errors
window.addEventListener("error", (event) => {
  if (
    event.message.includes("Could not establish connection") ||
    event.message.includes("Receiving end does not exist")
  ) {
    event.preventDefault();
    console.warn("Browser extension error filtered:", event.message);
    return false;
  }
});

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
