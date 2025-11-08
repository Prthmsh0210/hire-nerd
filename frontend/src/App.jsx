// src/App.jsx (Replace all content)

import React from 'react';
import { Routes, Route } from 'react-router-dom';
import HomePage from './components/HomePage';
import MainApp from './components/MainApp';
import AnimatedNebulaBackground from './components/AnimatedNebulaBackground';
import './App.css';

function App() {
  return (
    <div className="app">
      <AnimatedNebulaBackground />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/app" element={<MainApp />} />
      </Routes>
    </div>
  );
}

export default App;