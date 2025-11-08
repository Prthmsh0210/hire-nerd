// src/components/MainApp.jsx
import React, { useState } from 'react';
import UploadForm from './UploadForm';
import ResultTable from './ResultTable';
import CandidateProfileCard from './CandidateProfileCard';
import InterviewScheduler from './InterviewScheduler';
import DownloadButton from './DownloadButton';
import AIVoiceInterview from './AIVoiceInterview';
import UpcomingInterviews from './UpcomingInterviews'; // IMPORT NEW COMPONENT
import '../App.css';

function MainApp() {
  const [results, setResults] = useState([]);
  const [excelUrl, setExcelUrl] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedCandidateForInterview, setSelectedCandidateForInterview] = useState(null);
  const [selectedCandidateForScheduling, setSelectedCandidateForScheduling] = useState(null);
  const [showAIVoiceInterface, setShowAIVoiceInterface] = useState(false);
  const [showCandidateProfiles, setShowCandidateProfiles] = useState(false);
  const [showUpcomingInterviews, setShowUpcomingInterviews] = useState(false); // NEW STATE

  const handleStartAIVoiceInterview = (candidate) => {
    setSelectedCandidateForInterview(candidate);
    setSelectedCandidateForScheduling(null);
    setShowAIVoiceInterface(true);
    setShowUpcomingInterviews(false); // Hide other sections
  };

  const handleSelectCandidateForScheduling = (candidate) => {
    setSelectedCandidateForScheduling(candidate);
    setSelectedCandidateForInterview(null);
    setShowAIVoiceInterface(false);
    setShowUpcomingInterviews(false); // Hide other sections
  };

  const handleAIInterviewComplete = (updatedCandidateProfile) => {
    setResults(prevResults =>
      prevResults.map(res =>
        res.id === updatedCandidateProfile.id ? { ...res, ...updatedCandidateProfile } : res
      )
    );
    setSelectedCandidateForScheduling(updatedCandidateProfile); // Optionally auto-select for scheduling
    setShowAIVoiceInterface(false);
    setSelectedCandidateForInterview(null);
  };

  const handleCloseAIVoiceInterface = () => {
    setShowAIVoiceInterface(false);
    setSelectedCandidateForInterview(null);
  };

  const toggleShowCandidateProfiles = () => {
    setShowCandidateProfiles(prevShow => !prevShow);
    if (!showCandidateProfiles) { // If turning profiles on, hide other sections
        setShowUpcomingInterviews(false);
        setSelectedCandidateForScheduling(null);
    }
  };

  const toggleShowUpcomingInterviews = () => { // NEW HANDLER
    setShowUpcomingInterviews(prevShow => !prevShow);
    if (!showUpcomingInterviews) { // If turning interviews on, hide other sections
        setShowCandidateProfiles(false);
        setSelectedCandidateForScheduling(null);
        setShowAIVoiceInterface(false);
    }
  };

  // When new search results come, reset views
  const handleNewSearch = () => {
    setShowCandidateProfiles(false);
    setSelectedCandidateForScheduling(null);
    setSelectedCandidateForInterview(null);
    setShowAIVoiceInterface(false);
    setShowUpcomingInterviews(false);
  };


  return (
    <>
      <header className="app-header">
        <h1>HireNerd – Smart Recruitment Platform</h1>
        <p className="app-subtitle">Upload JD & Resumes to match candidates a find a Nerd for Your Team instantly</p>
      </header>

      <main className="app-main">
        {error && <div className="error-message" role="alert">{error}</div>}

        <div className="layout-container">
          <div className="upload-panel">
            <UploadForm
                setResults={setResults}
                setExcelUrl={setExcelUrl}
                setIsLoading={setIsLoading}
                setError={setError}
                onNewSearch={handleNewSearch} // Pass the handler
            />
          </div>

          <div className="results-panel">
            {isLoading && (
              <div className="loading-state results-panel-state avenger-loading">
                 <div className="avenger-spinner"></div>
                 <p>Assembling Intelligence... Stand By, Agent!</p>
              </div>
            )}

            {!isLoading && results.length === 0 && !error && (
                <div className="placeholder-results results-panel-state">
                    <p>Awaiting Your Command.</p>
                    <p>Upload a Job Description and Resumes to assemble your candidate roster.</p>
                </div>
            )}
            
            {!isLoading && results.length > 0 && !showUpcomingInterviews && ( // Conditionally hide if showing upcoming interviews
              <div className="results-content-scrollable">
                <ResultTable results={results} />
                
                <div className="action-buttons-bar">
                  {excelUrl && (
                      <DownloadButton url={excelUrl} label="Download Mission Report (XLSX)" />
                  )}
                  <button 
                    className="navigation-button view-profiles-button" 
                    onClick={toggleShowCandidateProfiles}
                  >
                    {showCandidateProfiles ? "Hide Candidate Dossiers" : "View Candidate Dossiers"}
                  </button>
                </div>
                
                <div className="section-divider"></div>

                <section className="upcoming-interviews-nav-section">
                  <h2>Interview Operations</h2>
                  <button className="navigation-button" onClick={toggleShowUpcomingInterviews}>
                    {showUpcomingInterviews ? "Hide Upcoming Briefings" : "View Upcoming Briefings"}
                  </button>
                  {/* Add a general schedule button if needed */}
                   <button 
                        className="navigation-button" 
                        onClick={() => {
                            setSelectedCandidateForScheduling({ name: "New Candidate" }); // Dummy for now
                            setShowCandidateProfiles(false);
                            setShowUpcomingInterviews(false);
                            setShowAIVoiceInterface(false);
                        }}
                        style={{backgroundColor: 'var(--accent-magenta)', color: 'white', borderColor: 'var(--accent-magenta)'}}
                    >
                        Schedule General Interview
                    </button>
                </section>
                
                <div className="section-divider"></div>

                {showCandidateProfiles && (
                  <section className="candidate-section">
                    <h2>Candidate Dossiers</h2>
                    <div className="candidate-grid">
                      {results.map((candidate, index) => (
                        <CandidateProfileCard
                          key={candidate.id || index}
                          candidate={candidate}
                          onSelect={() => handleSelectCandidateForScheduling(candidate)}
                          onStartAIVoiceInterview={() => handleStartAIVoiceInterview(candidate)}
                        />
                      ))}
                    </div>
                  </section>
                )}

                {showAIVoiceInterface && selectedCandidateForInterview && (
                  <section className="ai-voice-interview-section">
                    <div className="section-divider"></div>
                    <h2>AI Voice Interrogation: {selectedCandidateForInterview.name}</h2>
                    <AIVoiceInterview
                        candidate={selectedCandidateForInterview}
                        onInterviewComplete={handleAIInterviewComplete}
                        onClose={handleCloseAIVoiceInterface}
                    />
                  </section>
                )}

                {selectedCandidateForScheduling && !showAIVoiceInterface && (
                  <section className="scheduler-section">
                    <div className="section-divider"></div>
                    <h2>Schedule Follow-up: {selectedCandidateForScheduling.name}</h2>
                    <InterviewScheduler candidate={selectedCandidateForScheduling} />
                  </section>
                )}
              </div>
            )}
            {/* Display UpcomingInterviews when showUpcomingInterviews is true */}
            {!isLoading && showUpcomingInterviews && (
                 <div className="results-content-scrollable">
                    <section className="upcoming-interviews-nav-section">
                         <button className="navigation-button" onClick={toggleShowUpcomingInterviews} style={{marginBottom: '20px'}}>
                            {results.length > 0 ? "Back to Match Results" : "Back to Upload"}
                        </button>
                    </section>
                    <UpcomingInterviews />
                 </div>
            )}
          </div>
        </div>
      </main>

      <footer className="app-footer">
        <p>© {new Date().getFullYear()} HisbandHR.ai Initiative. All rights reserved. <a href="/privacy">Intel Protocol</a> | <a href="/terms">Service EULA</a></p>
      </footer>
    </>
  );
}

export default MainApp;