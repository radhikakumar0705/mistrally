import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

document.title = "Mistrally";


const favicon = document.createElement("link");
favicon.rel = "icon";
favicon.href = "%PUBLIC_URL%/favicon.ico"; // or use a custom path like "/my-icon.png"
document.head.appendChild(favicon);

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);