// src/components/DownloadButton.jsx
import React from 'react';
import './DownloadButton.css';

const DownloadButton = ({ url, label = "Download Excel Report" }) => {
  const handleClick = (e) => {
     if (!url || url === '#') { // MODIFIED: Check for placeholder '#'
       e.preventDefault();
       alert('Download link is not available or report is not ready yet.');
     }
   };

   return (
     <div className="download-button-wrapper">
       <a
         href={url || '#'} // Keep fallback for initial render
         download // This attribute suggests to the browser to download the linked URL
         className={`download-btn ${!url || url === '#' ? 'disabled' : ''}`}
         onClick={handleClick}
         aria-label={label}
         aria-disabled={!url || url === '#'}
       >
         📥 {label}
       </a>
     </div>
   );
};

export default DownloadButton;