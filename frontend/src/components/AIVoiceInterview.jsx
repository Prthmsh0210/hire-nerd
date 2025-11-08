// src/components/AIVoiceInterview.jsx (Conceptual - NOT PART OF THE PROVIDED FILES)
import React, { useState, useEffect, useRef } from 'react';
import './AIVoiceInterview.css'; // Import the new CSS
// import axios from 'axios'; // To send/receive data from backend

const AIVoiceInterview = ({ candidate, onInterviewComplete, onClose }) => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [aiResponse, setAiResponse] = useState('');
  const [currentQuestion, setCurrentQuestion] = useState('');
  // const [sentimentScore, setSentimentScore] = useState(null); // From backend using VADER

  // Refs for SpeechRecognition and SpeechSynthesis
  const recognitionRef = useRef(null);
  // ...

  useEffect(() => {
    // Initialize SpeechRecognition and SpeechSynthesis if available in browser
    // Example:
    // if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
    //   const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    //   recognitionRef.current = new SpeechRecognition();
    //   recognitionRef.current.continuous = false;
    //   recognitionRef.current.interimResults = true;
    //   recognitionRef.current.lang = 'en-US';
    //
    //   recognitionRef.current.onresult = (event) => { /* handle transcript */ };
    //   recognitionRef.current.onerror = (event) => { /* handle error */ };
    //   recognitionRef.current.onend = () => { /* handle end of listening */ };
    // } else {
    //   alert('Speech recognition not supported in this browser.');
    // }
    //
    // Initial question from backend or predefined
    // fetchInitialQuestion();
    setCurrentQuestion("Tell me about your experience with project management.");
    speakText("Tell me about your experience with project management.");

    return () => {
      // Cleanup: stop listening, stop synthesis
      // if (recognitionRef.current) recognitionRef.current.stop();
    };
  }, []);

  const speakText = (text) => {
    // if ('speechSynthesis' in window && text) {
    //   const utterance = new SpeechSynthesisUtterance(text);
    //   window.speechSynthesis.speak(utterance);
    //   setAiResponse(text); // Display what AI is saying
    // }
    setAiResponse(text); // For simulation
     console.log("AI Speaking:", text);
  };

  const handleStartListening = () => {
    // if (recognitionRef.current) {
    //   setTranscript('');
    //   setIsListening(true);
    //   recognitionRef.current.start();
    // }
    setIsListening(true);
    console.log("Listening started...");
    // Simulate user speaking after a delay
    setTimeout(() => {
        const simulatedTranscript = "I have managed several large projects using Agile methodologies.";
        setTranscript(simulatedTranscript);
        setIsListening(false);
        console.log("Listening stopped. Transcript:", simulatedTranscript);
        sendTranscriptToBackend(simulatedTranscript);
    }, 3000);
  };

  const sendTranscriptToBackend = async (userText) => {
    // console.log("Sending to backend:", userText);
    // try {
    //   const response = await axios.post(`/api/ai-interview/${candidate.id}/converse`, { text: userText });
    //   const { nextQuestion, sentiment, interviewData } = response.data;
    //   setCurrentQuestion(nextQuestion);
    //   setSentimentScore(sentiment); // VADER score from backend
    //   speakText(nextQuestion);
    //   if (response.data.isComplete) {
    //      onInterviewComplete(interviewData); // Pass updated candidate profile
    //   }
    // } catch (error) {
    //   console.error("Error during AI conversation:", error);
    //   speakText("I'm sorry, I encountered an issue. Let's try that again or please contact support.");
    // }
    // Simulate backend response
    const nextQuestion = "That's interesting. Can you elaborate on a challenge you faced?";
    setCurrentQuestion(nextQuestion);
    speakText(nextQuestion);
    // Simulate sentiment from VADER (processed on backend)
    // setSentimentScore({ type: 'Positive', compound: 0.7 });
  };

    return (
    // <div style={{ border: '1px solid #ddd', padding: '20px', borderRadius: '8px' }}>
    <div className="ai-voice-interview-container">
      <h4>AI Voice Interview: {candidate.name}</h4>
      <div style={{ marginBottom: '15px' }}> {/* Adjusted margin */}
        <strong>AI:</strong> <span id="ai-response-display">{aiResponse || currentQuestion}</span>
      </div>
      <div style={{ marginBottom: '15px' }}> {/* Adjusted margin */}
        <strong>You:</strong> <span id="user-transcript-display">{transcript}</span>
      </div>
      {!isListening ? (
        <button onClick={handleStartListening} disabled={!currentQuestion || aiResponse === "I'm sorry, I encountered an issue. Let's try that again or please contact support."}>
          🎤 Speak Response
        </button>
      ) : (
        <p>Listening...</p>
      )}
      <button onClick={() => onInterviewComplete({ ...candidate, aiInterviewScore: 3.8, sentimentAnalysis: { overall: 'Neutral', score: 0.2 } })}>
        Simulate End Interview
      </button>
      <button onClick={onClose} style={{ backgroundColor: 'var(--red-flag-color)', color: 'white' }}>Close</button>
    </div>
  );
};

export default AIVoiceInterview;