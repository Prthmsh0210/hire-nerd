// src/components/InterviewScheduler.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './InterviewScheduler.css';

const InterviewScheduler = ({ candidate }) => {
  const [date, setDate] = useState('');
  const [time, setTime] = useState('');
  const [candidateEmail, setCandidateEmail] = useState(candidate?.email || ''); // Pre-fill if available
  const [interviewerEmails, setInterviewerEmails] = useState(''); // Comma-separated
  const [duration, setDuration] = useState(30); // Default duration
  
  const [isScheduling, setIsScheduling] = useState(false);
  const [scheduleResult, setScheduleResult] = useState(null);

  // Update candidate email if candidate prop changes
  useEffect(() => {
    setCandidateEmail(candidate?.email || '');
  }, [candidate]);

  const handleSchedule = async () => {
    if (!date || !time || !candidateEmail || !interviewerEmails || !duration) {
      alert('Please fill in all fields: date, time, candidate email, interviewer emails, and duration.');
      return;
    }

    const selectedDateTime = new Date(`${date}T${time}`);
    if (selectedDateTime <= new Date()) {
      alert('Please choose a future date and time for the interview.');
      return;
    }

    const startTimeISO = selectedDateTime.toISOString();
    
    const formData = new FormData();
    formData.append('candidate_name', candidate.name);
    formData.append('candidate_email', candidateEmail);
    formData.append('interviewer_emails', interviewerEmails); // Send as comma-separated string
    formData.append('start_time', startTimeISO);
    formData.append('duration_minutes', parseInt(duration, 10));

    setIsScheduling(true);
    setScheduleResult(null);

    try {
      const response = await axios.post('/api/schedule-interview', formData); // Proxy handles this

      if (response.data.error) {
          throw new Error(response.data.error);
      }

      setScheduleResult({
          meet_link: response.data.meet_link,
          time: new Date(startTimeISO).toLocaleString(),
          success: true,
          calendar_link: response.data.event_link
      });
      alert(`Interview scheduled successfully for ${candidate.name}! Meet link: ${response.data.meet_link}`);

    } catch (error) {
      console.error("Error scheduling interview:", error);
      let errorMessage = "Failed to schedule interview. ";
      if (error.response && error.response.status === 401) {
        // Make the authorization URL clickable if it's in the detail
        if (error.response.data && error.response.data.detail && error.response.data.detail.includes("http")) {
            const authUrl = error.response.data.detail.substring(error.response.data.detail.indexOf("http"));
            errorMessage = (
                <span>
                    Authentication required. Please <a href={authUrl} target="_blank" rel="noopener noreferrer">authorize your Google Account</a>.
                </span>
            );
        } else {
            errorMessage += "Authentication required. Please authorize your Google Account (check backend logs for URL).";
        }
      } else if (error.response && error.response.data && error.response.data.detail) {
        errorMessage += error.response.data.detail;
      }
      else {
        errorMessage += "Please check backend logs or console for details.";
      }
      setScheduleResult({ error: errorMessage, success: false });
    } finally {
      setIsScheduling(false);
    }
  };

  return (
    <div className="scheduler-container">
      <h3>Schedule Interview for {candidate.name}</h3>
      <div className="scheduler-form">
        <label>
          Candidate Email:
          <input
            type="email"
            value={candidateEmail}
            onChange={(e) => setCandidateEmail(e.target.value)}
            placeholder="candidate@example.com"
            required
          />
        </label>
        <label>
          Interviewer Email(s) (comma-separated):
          <input
            type="text"
            value={interviewerEmails}
            onChange={(e) => setInterviewerEmails(e.target.value)}
            placeholder="hr1@example.com, hr2@example.com"
            required
          />
        </label>
        <label>
          Date:
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            required
            min={new Date().toISOString().split("T")[0]}
          />
        </label>
        <label>
          Time:
          <input
            type="time"
            value={time}
            onChange={(e) => setTime(e.target.value)}
            required
          />
        </label>
        <label>
          Duration:
          <select value={duration} onChange={(e) => setDuration(parseInt(e.target.value, 10))} required>
            <option value="20">20 minutes</option>
            <option value="30">30 minutes</option>
            <option value="45">45 minutes</option>
            <option value="60">60 minutes</option>
          </select>
        </label>
        <button type="button" onClick={handleSchedule} disabled={isScheduling}>
          {isScheduling ? 'Scheduling...' : 'Schedule Interview'}
        </button>
      </div>

      {scheduleResult && scheduleResult.success && (
        <div className="scheduled-details">
          <p>
            <span role="img" aria-label="calendar" className="icon-calendar">📅</span> Scheduled for <strong>{scheduleResult.time}</strong>
          </p>
          {scheduleResult.meet_link && (
             <p>
              <span role="img" aria-label="link" className="icon-meet">🔗</span> Meet Link:{' '}
              <a href={scheduleResult.meet_link} target="_blank" rel="noopener noreferrer">
                Join Google Meet
              </a>
            </p>
          )}
          {scheduleResult.calendar_link && (
            <p>
                <span role="img" aria-label="calendar-event" className="icon-calendar">🗓️</span> Calendar Event:{' '}
                <a href={scheduleResult.calendar_link} target="_blank" rel="noopener noreferrer">
                    View Event
                </a>
            </p>
          )}
          <div className="status-box reminder-sent">
            <span role="img" aria-label="check" className="icon-check">✅</span> Event created in Google Calendar
          </div>
        </div>
      )}
      {scheduleResult && scheduleResult.error && (
         <div className="scheduled-details error-box">
            <p className="error-text">{scheduleResult.error}</p>
         </div>
      )}
    </div>
  );
};

export default InterviewScheduler;