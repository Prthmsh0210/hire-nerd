// src/components/CandidateProfileCard.jsx
import React from 'react';
import './CandidateProfileCard.css';

const CandidateProfileCard = ({ candidate, onSelect, onStartAIVoiceInterview }) => {

  const handleReuseProfile = (e) => {
    e.stopPropagation(); // Important to prevent the card's onSelect from firing
    alert(`Reusing profile for ${candidate.name}. (Functionality to be implemented)`);
  };

  // Determine if AI interview has been conducted (e.g., based on aiInterviewScore presence)
  const aiInterviewConducted = candidate.aiInterviewScore !== undefined && candidate.aiInterviewScore !== null;

  return (
    <div
      className="profile-card"
      onClick={onSelect} // This will be triggered if clicks are not stopped on buttons
      role="button"
      tabIndex="0"
      onKeyDown={(e) => e.key === 'Enter' && onSelect()}
    >
      <div className="profile-header">
        <div className="profile-image">
          <img src={candidate.profilePicture || 'https://via.placeholder.com/80'} alt={`${candidate.name}'s Profile`} />
        </div>
        <div className="profile-details">
          <h3>{candidate.name}</h3>
          <p>{candidate.role || 'Role not specified'}</p>
          
          {/* NEW: Contact Info Section */}
          <div className="contact-info">
            {candidate.email && (
              <span>
                <span role="img" aria-label="email" className="icon">📧</span>
                {candidate.email}
              </span>
            )}
            {candidate.phone && (
              <span>
                <span role="img" aria-label="phone" className="icon">📞</span>
                {candidate.phone}
              </span>
            )}
          </div>
        </div>
      </div>
      
      {/* JD Fit and AI Interview scores are now grouped here for a cleaner layout */}
      <div className="interview-score" style={{ marginTop: '0', marginBottom: '1rem' }}>
          <span>JD Fit:</span>
          <span>{typeof candidate.jdFit === 'number' ? `${candidate.jdFit.toFixed(0)}%` : 'N/A'}</span>
      </div>
      
      {aiInterviewConducted && (
        <div className="interview-score" style={{ marginTop: '-0.5rem', marginBottom: '1rem', color: candidate.aiInterviewScore >= 3.5 ? 'var(--jd-fit-green-text)' : 'var(--jd-fit-red-text)' }}>
            <span>AI Voice Interview:</span>
            <span>{typeof candidate.aiInterviewScore === 'number' ? `${candidate.aiInterviewScore.toFixed(1)}/5` : 'N/A'}</span>
        </div>
      )}

      <div className="profile-content">
        {candidate.redFlags && candidate.redFlags.length > 0 && (
          <div className="red-flags">
            <h4>Red Flags</h4>
            <ul>
              {candidate.redFlags.map((flag, idx) => (
                <li key={idx}>{typeof flag === 'object' ? flag.description : flag}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="experience-summary">
          <h4>Experience Summary</h4>
          <p>{candidate.experienceSummary || 'Summary not available.'}</p>
        </div>

        <div className="scorecard">
          <h4>Scorecard Breakdown</h4>
          <div className="score-item">
            <span>Communication</span>
            <div className="progress-bar-container">
              <div className="progress-bar-fill" style={{ width: `${(candidate.communication || 0) * 10}%` }}></div>
            </div>
            <span>{candidate.communication || 0}</span>
          </div>
          {/* Display VADER sentiment analysis results if available */}
          {candidate.sentimentAnalysis && (
            <div className="score-item" style={{marginTop: '10px'}}>
                <span>Sentiment (VADER):</span>
                <span style={{
                    color: candidate.sentimentAnalysis.overall === 'Positive' ? 'var(--jd-fit-green-text)' : 
                           (candidate.sentimentAnalysis.overall === 'Negative' ? 'var(--jd-fit-red-text)' : 'var(--jd-fit-yellow-text)')
                }}>
                    {candidate.sentimentAnalysis.overall || 'Neutral'}
                    {typeof candidate.sentimentAnalysis.score === 'number' && ` (${candidate.sentimentAnalysis.score.toFixed(2)})`}
                </span>
            </div>
          )}
        </div>
      </div>

      {/* Button section from the original component */}
      <div className="profile-card-actions">
        <button
          className="profile-action-btn"
          onClick={handleReuseProfile}
        >
          Reuse Profile
        </button>
        
        {onStartAIVoiceInterview && !aiInterviewConducted && (
            <button
                className="profile-action-btn ai-interview-btn"
                onClick={(e) => {
                    e.stopPropagation(); // Prevent card's onSelect
                    onStartAIVoiceInterview(candidate);
                }}
            >
                Start AI Voice Interview
            </button>
        )}
        {aiInterviewConducted && (
            <span className="ai-interview-status">AI Interviewed</span>
        )}
      </div>
    </div>
  );
};

export default CandidateProfileCard;