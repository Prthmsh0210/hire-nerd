// src/components/UpcomingInterviews.jsx (New File)
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './UpcomingInterviews.css'; // Create this CSS file next

const UpcomingInterviews = () => {
  const [interviews, setInterviews] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchInterviews = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await axios.get('/api/upcoming-interviews'); // Proxy handles this
        setInterviews(response.data);
      } catch (err) {
        console.error('Error fetching upcoming interviews:', err);
        let errorMessage = 'Failed to load upcoming interviews.';
        if (err.response && err.response.status === 401) {
            errorMessage += " Authentication required. Please authorize your Google Account via the backend /authorize endpoint.";
        } else if (err.response && err.response.data && err.response.data.detail) {
            errorMessage += ` ${err.response.data.detail}`;
        }
        setError(errorMessage);
        setInterviews([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchInterviews();
  }, []);

  if (isLoading) {
    return <div className="loading-state results-panel-state avenger-loading">Loading upcoming interviews...</div>;
  }

  if (error) {
    return <div className="error-message" style={{textAlign: 'center', padding: '20px'}}>{error}</div>;
  }

  return (
    <div className="upcoming-interviews-container">
      <h2>Upcoming Interview Briefings</h2>
      {interviews.length === 0 ? (
        <p className="no-interviews-message">No upcoming interviews scheduled yet.</p>
      ) : (
        <ul className="interviews-list">
          {interviews.map((interview) => (
            <li key={interview.id} className="interview-item-card">
              <h3>{interview.candidate_name}</h3>
              <p><strong>Candidate Email:</strong> {interview.candidate_email}</p>
              <p>
                <strong>Date & Time:</strong>{' '}
                {new Date(interview.start_time).toLocaleString()}
              </p>
              <p><strong>Duration:</strong> {interview.duration_minutes} minutes</p>
              <p>
                <strong>Interviewers:</strong> {interview.interviewer_emails.join(', ')}
              </p>
              {interview.google_meet_link && (
                <p>
                  <strong>Meet Link:</strong>{' '}
                  <a href={interview.google_meet_link} target="_blank" rel="noopener noreferrer">
                    Join Meeting
                  </a>
                </p>
              )}
               {interview.google_calendar_link && (
                <p>
                  <strong>Calendar Event:</strong>{' '}
                  <a href={interview.google_calendar_link} target="_blank" rel="noopener noreferrer">
                    View in Calendar
                  </a>
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default UpcomingInterviews;