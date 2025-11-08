// src/components/AnimatedNebulaBackground.jsx
import React from 'react';

const AnimatedNebulaBackground = () => {
  // We use three nested divs to create three independent star layers for a parallax effect.
  return (
    <div className="nebula-background">
      <div className="stars1"></div>
      <div className="stars2"></div>
      <div className="stars3"></div>
    </div>
  );
};

export default AnimatedNebulaBackground;