// src/components/AnalyticsDashboard.jsx
import React, { useEffect, useRef, useState } from 'react';
import Chart from 'chart.js/auto';
import axios from 'axios'; // NEW: Import axios
import './AnalyticsDashboard.css';

const AnalyticsDashboard = () => {
  const pieChartRef = useRef(null);
  const barChartRef = useRef(null);
  const [dashboardData, setDashboardData] = useState({
    pieData: [], // Initial empty state
    barData: [], // Initial empty state
    noShows: 0,
    upcomingInterviews: 0,
    autoMatchedProfiles: 0,
    upcomingInterviewsDetails: [],
    // NEW: Add funnel data, CQI trends, red flag frequency (as examples)
    funnelStages: { labels: [], data: [] },
    cqiTrend: { labels: [], data: [] },
    redFlagFrequency: { labels: [], data: [] },
  });
  const [isLoading, setIsLoading] = useState(true); // NEW: Loading state for dashboard data
  const [error, setError] = useState(null); // NEW: Error state for dashboard data

  useEffect(() => {
    const fetchDashboardData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        // THIS IS THE LINE MAKING THE REQUEST
        const response = await axios.get('/api/analytics'); // NEW: Actual API call
        
        // This part processes the successful response
        setDashboardData({
          ...dashboardData, // Keep any defaults if not overridden by API
          ...response.data,
          // Ensure nested objects are handled if API structure differs
          pieData: response.data.pieData || [],
          barData: response.data.barData || [],
          upcomingInterviewsDetails: response.data.upcomingInterviewsDetails || [],
          funnelStages: response.data.funnelStages || { labels: [], data: [] },
          cqiTrend: response.data.cqiTrend || { labels: [], data: [] },
          redFlagFrequency: response.data.redFlagFrequency || { labels: [], data: [] },
        });
      } catch (err) {
        // This part handles the error if the axios.get call fails
        console.error('Failed to load analytics:', err);
        setError('Failed to load analytics data. Please try again later.'); // This is the error message you are seeing
        // Fallback to empty or default data to prevent chart errors
        setDashboardData({
          pieData: [61, 28, 11], // Example fallback
          barData: [50, 60, 70, 80, 90], // Example fallback
          noShows: 2,
          upcomingInterviews: 5,
          autoMatchedProfiles: 3,
          upcomingInterviewsDetails: [
            { name: 'Tejas Kulkarni', role: 'AVP SALES', date: 'April 11' },
          ],
          funnelStages: { labels: ['Applied', 'Screened', 'Interviewed', 'Offered', 'Hired'], data: [100,70,40,20,10] },
          cqiTrend: { labels: ['Jan', 'Feb', 'Mar'], data: [65, 70, 75] },
          redFlagFrequency: { labels: ['Job Hopping', 'Skill Mismatch'], data: [5, 3] },
        });
      } finally {
        setIsLoading(false);
      }
    };
    fetchDashboardData();
  }, []); // Fetch data on component mount

  useEffect(() => {
    let pieChartInstance;
    let barChartInstance;
    // TODO: Add instances for new charts (funnel, cqiTrend, redFlagFrequency)

    if (pieChartRef.current && dashboardData.pieData.length > 0) {
      const ctxPie = pieChartRef.current.getContext('2d');
      pieChartInstance = new Chart(ctxPie, {
        type: 'pie',
        data: {
          labels: ['Reviewed', 'In Progress', 'Skipped'], // These labels could also come from API
          datasets: [{
            data: dashboardData.pieData,
            backgroundColor: ['#2ecc71', '#f1c40f', '#e74c3c']
          }]
        },
        options: {
          responsive: true,
          plugins: {
            legend: { position: 'bottom' }
          }
        }
      });
    }

    if (barChartRef.current && dashboardData.barData.length > 0) {
      const ctxBar = barChartRef.current.getContext('2d');
      barChartInstance = new Chart(ctxBar, {
        type: 'bar',
        data: {
          labels: ['Jan.', 'Feb.', 'Mar.', 'Apr.', 'May'], // These labels could also come from API
          datasets: [{
            label: 'Average CQI',
            data: dashboardData.barData,
            backgroundColor: '#3b82f6'
          }]
        },
        options: {
          responsive: true,
          plugins: {
            legend: { display: false }
          }
        }
      });
    }
    return () => {
     if (pieChartInstance) pieChartInstance.destroy();
     if (barChartInstance) barChartInstance.destroy();
     // TODO: Destroy new chart instances
    }
  }, [dashboardData]); // Re-render charts when data changes

  if (isLoading) {
    return <div className="loading-state">Loading analytics...</div>;
  }

  if (error) {
    return <div className="error-message" style={{textAlign: 'center', padding: '20px'}}>{error}</div>;
  }

  return (
    <div className="analytics-dashboard">
      <h2>Recruitment Analytics</h2>
      <div className="chart-container">
        <div className="chart-box">
          <canvas ref={pieChartRef}></canvas>
          <p>Resume Review Status</p>
        </div>
        <div className="chart-box">
          <canvas ref={barChartRef}></canvas>
          <p>Average CQI Over Time</p>
        </div>
        {/* NEW: Placeholder for more charts based on FTN */}
        {/*
        <div className="chart-box">
          <canvas ref={funnelChartRef}></canvas>
          <p>Hiring Funnel Stages</p>
        </div>
        <div className="chart-box">
          <canvas ref={redFlagChartRef}></canvas>
          <p>Red Flag Frequency</p>
        </div>
        */}
      </div>

      <div className="metrics-section">
        <div className="metric-card">
          <span className="metric-value">{dashboardData.noShows}</span>
          <span className="metric-label">No-Shows</span>
        </div>
        <div className="metric-card">
          <span className="metric-value">{dashboardData.upcomingInterviews}</span>
          <span className="metric-label">Upcoming Interviews</span>
        </div>
        <div className="metric-card">
          <span className="metric-value">{dashboardData.autoMatchedProfiles}</span>
          <span className="metric-label">Auto-Matched Profiles</span>
        </div>
      </div>

      {/* NEW: Render upcomingInterviewsDetails */}
      {dashboardData.upcomingInterviewsDetails && dashboardData.upcomingInterviewsDetails.length > 0 && (
        <div className="additional-info">
          <div className="info-card">
            <h3 className="info-title">Upcoming Interview Details</h3>
            <ul className="interview-list">
              {dashboardData.upcomingInterviewsDetails.map((interview, index) => (
                <li key={index} className="interview-item">
                  <strong>{interview.name}</strong> - {interview.role} on {interview.date}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

export default AnalyticsDashboard;