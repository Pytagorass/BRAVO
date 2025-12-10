/**
 * index.js
 * --------
 * Realiza o bootstrap da aplicação React: importa estilos globais e
 * monta o componente <App /> dentro do React.StrictMode.
 */
import 'bootstrap/dist/css/bootstrap.min.css';
import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

reportWebVitals();
