// src/components/UploadForm.jsx
import React, { useState } from 'react';
import axios from 'axios';
import './UploadForm.css';

const UploadForm = ({
  setResults,
  setExcelUrl,
  setIsLoading,
  setError,
  onNewSearch, // <-- Add this prop
}) => {
  const [jdFile, setJdFile] = useState(null);
  const [resumeFiles, setResumeFiles] = useState([]);
  const [internalIsLoading, setInternalIsLoading] = useState(false);
  const [consentGiven, setConsentGiven] = useState(false);

  const handleJDChange = (e) => {
    if (e.target.files.length > 0) {
      setJdFile(e.target.files[0]);
    } else {
      setJdFile(null);
    }
  };

  const handleResumesChange = (e) => {
    if (e.target.files.length > 0) {
      setResumeFiles(Array.from(e.target.files));
    } else {
      setResumeFiles([]);
    }
  };

  const handleConsentChange = (e) => {
    setConsentGiven(e.target.checked);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!jdFile || resumeFiles.length === 0) {
      setError('Please upload both a Job Description and at least one resume.');
      return;
    }
    if (!consentGiven) {
      setError('Please agree to the terms by checking the consent box.');
      return;
    }

     if (onNewSearch) onNewSearch(); // <-- Call this before setting loading

    setIsLoading(true);
    setInternalIsLoading(true);
    setError(null);
    setResults([]);
    setExcelUrl(null);

    const formData = new FormData();
    formData.append('jd', jdFile);
    for (let i = 0; i < resumeFiles.length; i++) {
      formData.append('resumes', resumeFiles[i]);
    }

    // Define the backend base URL for constructing the Excel download link.
    // This is NOT used for the axios.post call if the proxy is working.
    const BACKEND_BASE_URL_FOR_LINKS = 'http://localhost:8000';

    try {
      // With the Vite proxy configured in vite.config.js,
      // this relative path '/api/match' will be forwarded to http://localhost:8000/api/match
      const response = await axios.post('/api/match', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setResults(response.data.results || []);

      // The backend returns excelUrl as a relative path like "/static/reports/file.xlsx".
      // We need to prepend the backend's base URL for the download link to work correctly
      // when clicked in the frontend (which is on a different port).
      let finalExcelUrl = null;
      if (response.data.excelUrl) {
        if (response.data.excelUrl.startsWith('/')) {
          finalExcelUrl = `${BACKEND_BASE_URL_FOR_LINKS}${response.data.excelUrl}`;
        } else {
          // In case the backend ever sends an absolute URL, use it directly
          finalExcelUrl = response.data.excelUrl;
        }
      }
      setExcelUrl(finalExcelUrl);

      if (!response.data.results || response.data.results.length === 0) {
        setError('No matching candidates found. Try adjusting your JD or resumes.');
      }
    } catch (err) {
      console.error('Matching error:', err);
      let errorMessage = 'Something went wrong during matching. Please try again.';
      if (err.response) {
        console.error("Backend Error Response Data:", err.response.data);
        console.error("Backend Error Response Status:", err.response.status);
        if (err.response.data && err.response.data.detail) {
            errorMessage = `Error from server (${err.response.status}): ${err.response.data.detail}`;
        } else if (err.response.data && err.response.data.message) {
            errorMessage = `Error from server (${err.response.status}): ${err.response.data.message}`;
        } else if (err.response.status === 404) {
            errorMessage = 'API endpoint not found (404). Check the proxy and backend URL.';
        } else {
            errorMessage = `Server error (${err.response.status}). Check backend logs.`;
        }
      } else if (err.request) {
        console.error("No response received:", err.request);
        errorMessage = 'No response from server. Is the backend running and proxy configured?';
      } else {
        console.error('Error setting up request:', err.message);
      }
      setError(errorMessage);
      setResults([]);
      setExcelUrl(null);
    } finally {
      setIsLoading(false);
      setInternalIsLoading(false);
    }
  };

  return (
    <div className="upload-form-container">
      <h2>Upload Job Description & Resumes</h2>
      <form onSubmit={handleSubmit} className="upload-form">
        {/* JD Upload */}
        <div className="upload-group">
          <label htmlFor="jd-upload" className="upload-label">
            📄 Upload Job Description (PDF/TXT/DOCX)
          </label>
          <input
            id="jd-upload"
            type="file"
            accept=".txt,.pdf,.doc,.docx"
            onChange={handleJDChange}
            className="upload-input"
            required
          />
          {jdFile && <span className="file-name">{jdFile.name}</span>}
        </div>

        {/* Resume Upload */}
        <div className="upload-group">
          <label htmlFor="resume-upload" className="upload-label">
            🧾 Upload Candidate Resumes (Multiple PDF/DOCX Accepted)
          </label>
          <input
            id="resume-upload"
            type="file"
            accept=".pdf,.doc,.docx"
            multiple
            onChange={handleResumesChange}
            className="upload-input"
            required
          />
          {resumeFiles.length > 0 && (
            <ul className="file-list">
              {resumeFiles.map((file, index) => (
                <li key={index} className="file-item">
                  {file.name} ({ (file.size / 1024).toFixed(2) } KB)
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Consent Checkbox */}
        <div className="consent-group">
          <input
            type="checkbox"
            id="consent"
            name="consent"
            checked={consentGiven}
            onChange={handleConsentChange}
          />
          <label htmlFor="consent" className="consent-label">
            I consent to the processing of uploaded data as per the <a href="/privacy-policy" target="_blank" rel="noopener noreferrer">Privacy Policy</a>.
          </label>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={internalIsLoading || !jdFile || resumeFiles.length === 0 || !consentGiven}
          className={`submit-button marvel-submit-button ${ (internalIsLoading || !jdFile || resumeFiles.length === 0 || !consentGiven) ? 'disabled' : ''}`}
        >
          {internalIsLoading ? 'Scanning a Nerd...' : 'Lets Find a Nerd!'}
        </button>
      </form>
    </div>
  );
};

export default UploadForm;