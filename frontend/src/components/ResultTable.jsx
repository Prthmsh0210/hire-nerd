// src/components/ResultTable.jsx
import React from 'react';
import './ResultTable.css'; // Import CSS

const ResultTable = ({ results }) => {
  const getFitClass = (score) => {
    if (score >= 80) return 'green';
    if (score >= 60) return 'yellow';
    return 'red';
  };

  if (!results || results.length === 0) {
    return (
      <div className="result-table-container">
        <h2>Matching Results</h2>
        <p className="no-results">No candidates matched yet.</p>
      </div>
    );
  }

  return (
    <div className="result-table-container">
      <h2>Matching Results</h2>
      <div className="table-wrapper">
        <table className="result-table">
          <thead>
            <tr>
              <th>Candidate Name</th>
              <th>JD Fit (%)</th>
              <th>Interview Score</th>
              <th>Red Flags</th>
            </tr>
          </thead>
          <tbody>
            {results.map((candidate, index) => (
              <tr key={candidate.id || index} className="candidate-row">
                <td>{candidate.name}</td>
                <td>
                  <span className={`jd-fit ${getFitClass(candidate.jdFit)}`}>
                    {candidate.jdFit}%
                  </span>
                </td>
                <td>{candidate.interviewScore}/5</td>
                <td>
                  {candidate.redFlags && candidate.redFlags.length > 0 ? (
                    <ul className="red-flag-list">
                      {candidate.redFlags.map((flag, idx) => (
                        <li key={idx} className="red-flag-item">
                          {flag}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <span className="no-red-flags">None</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ResultTable;