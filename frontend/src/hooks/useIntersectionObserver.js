// src/hooks/useIntersectionObserver.js (New File)
import { useState, useEffect, useRef } from 'react';

export const useIntersectionObserver = (options) => {
  const containerRef = useRef(null);
  const [isVisible, setIsVisible] = useState(false);

  const callbackFunction = (entries) => {
    const [entry] = entries;
    if (entry.isIntersecting) {
      setIsVisible(true);
      // Optional: Stop observing after it's visible once
      if (containerRef.current) {
        observer.unobserve(containerRef.current);
      }
    }
  };

  const observer = new IntersectionObserver(callbackFunction, options);

  useEffect(() => {
    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    return () => {
      if (containerRef.current) {
        observer.unobserve(containerRef.current);
      }
    };
  }, [containerRef, options]);

  return [containerRef, isVisible];
};