// src/components/HomePage.jsx
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useIntersectionObserver } from '../hooks/useIntersectionObserver';
import './HomePage.css';

// The images for the carousel. Make sure these files exist in your /public folder.
const carouselImages = [
  '/jd.png',
  '/RM1.png',
  '/RM2.png',
];

// Helper component for feature cards
const FeatureCard = ({ icon, title, description }) => {
  const [ref, isVisible] = useIntersectionObserver({ threshold: 0.1 });
  return (
    <div ref={ref} className={`feature-card ${isVisible ? 'is-visible' : ''}`}>
      <div className="feature-icon">{icon}</div>
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
};

// Helper component for "How it Works" steps
const HowItWorksStep = ({ number, title }) => {
    const [ref, isVisible] = useIntersectionObserver({ threshold: 0.5 });
    return (
        <div ref={ref} className={`how-step ${isVisible ? 'is-visible' : ''}`}>
            <div className="how-number">{number}</div>
            <p>{title}</p>
        </div>
    );
};


const HomePage = () => {
  const [activeIndex, setActiveIndex] = useState(0);
  const [heroRef, isHeroVisible] = useIntersectionObserver({ threshold: 0.2 });
  const [featuresRef, isFeaturesVisible] = useIntersectionObserver({ threshold: 0.1 });
  const [howItWorksRef, isHowItWorksVisible] = useIntersectionObserver({ threshold: 0.1 });

  // This effect handles the automatic rotation of the carousel
  useEffect(() => {
    const interval = setInterval(() => {
      setActiveIndex((prevIndex) => (prevIndex + 1) % carouselImages.length);
    }, 4000); // Change image every 4 seconds

    return () => clearInterval(interval); // Cleanup on component unmount
  }, []);

  return (
    <div className="home-page">
      {/* Hero Section */}
      <section ref={heroRef} className={`hero-section fade-in-section ${isHeroVisible ? 'is-visible' : ''}`}>
        <div className="hero-content">
          <h1>Hiring Just Got Human Again.
            <br />
            <span className="powered-by-ai">Powered by AI</span>
          </h1>
          <p>
            Automate shortlisting, calling, and scheduling — while keeping
            humanity at the core.
          </p>
          <div className="hero-cta">
            <Link to="/app" className="btn btn-primary">Try Demo</Link>
            <Link to="/app" className="btn btn-secondary">Upload JD + Resumes</Link>
          </div>
        </div>
        
        {/* MODIFIED: This is the new structure for the 3D rotating carousel */}
        <div className="hero-image">
          <div className="carousel-stage">
            {carouselImages.map((src, index) => (
              <img
                key={src}
                src={src}
                alt={`Hiring process visual ${index + 1}`}
                className={`carousel-image ${index === activeIndex ? 'active' : ''}`}
              />
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features-section">
        <div ref={featuresRef} className={`section-header fade-in-section ${isFeaturesVisible ? 'is-visible' : ''}`}>
            <h2>One Click, One Result.</h2>
            <p>Let HireNerd do the grunt work. You focus on what matters.</p>
        </div>
        <div className="features-grid">
            <FeatureCard icon="📄" title="Resume Parsing" description="JD and resume analysis using advanced NLP for deep shortlisting." />
            <FeatureCard icon="🤖" title="AI Calling & Scorecard" description="Assess skills, schedule interviews, and get a data-backed scorecard." />
            <FeatureCard icon="📅" title="Google Meet Integration" description="Seamlessly schedule interviews with automatic reminders." />
            <FeatureCard icon="📊" title="Dashboard & Analytics" description="Track your talent pipeline and view insightful metrics." />
        </div>
      </section>

      {/* How It Works Section */}
      <section className="how-it-works-section">
        <div ref={howItWorksRef} className={`section-header fade-in-section ${isHowItWorksVisible ? 'is-visible' : ''}`}>
            <h2>How It Works</h2>
        </div>
        <div className="how-steps-container">
            <HowItWorksStep number="1" title="Upload JD + Resumes" />
            <div className="how-arrow">→</div>
            <HowItWorksStep number="2" title="Get AI-Scored Matches" />
            <div className="how-arrow">→</div>
            <HowItWorksStep number="3" title="Let AI Call & Schedule" />
            <div className="how-arrow">→</div>
            <HowItWorksStep number="4" title="Download Reports" />
            <div className="how-arrow">→</div>
            <HowItWorksStep number="5" title="Hire Smarter, Faster" />
        </div>
      </section>
      
    </div>
  );
};

export default HomePage;