import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './App.css';

// Define types for our response data
interface HeadingInfo {
  [key: string]: string;
}

interface ContentInfo {
  information: {
    headings: HeadingInfo;
  };
}

interface SuccessResponse {
  success: true;
  information: ContentInfo;
  storage_success: boolean;
  error: null;
}

interface ErrorResponse {
  information: null;
  success: false;
  error: string;
  status_code: number;
}

type HarvestResponse = SuccessResponse | ErrorResponse;

function App() {
  const navigate = useNavigate();
  const params = useParams<{ tenant_id: string }>();
  const tenant_id = params.tenant_id;
  const [url, setUrl] = useState('');
  const [result, setResult] = useState<HarvestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [buttonStatus, setButtonStatus] = useState<'default' | 'success' | 'error'>('default');

  // Effect to reset button status after 10 seconds
  useEffect(() => {
    if (buttonStatus !== 'default') {
      const timer = setTimeout(() => {
        setButtonStatus('default');
      }, 10000);
      
      return () => clearTimeout(timer);
    }
  }, [buttonStatus]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    setButtonStatus('default');
    
    if (!tenant_id) {
      setError('Error: Tenant ID is undefined');
      setLoading(false);
      setButtonStatus('error');
      return;
    }

    try {
      const response = await fetch(`http://localhost:8000/v1/tenants/${tenant_id}/harvest/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `url=${encodeURIComponent(url)}`,
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.content.error || 'Unknown error occurred');
      }
      setResult(data.content);
      setButtonStatus(data.content.success ? 'success' : 'error');
    } catch (error) {
      setError(`Error: ${error instanceof Error ? error.message : 'Failed to fetch results'}`);
      setButtonStatus('error');
    }
    setLoading(false);
  };

  // Component to display successful harvest results
  function SuccessResult({ data }: { data: SuccessResponse }) {
    const [expandedHeadings, setExpandedHeadings] = useState<Set<string>>(new Set());

    if (!data.information?.information?.headings) {
      return <div className="no-data">No heading information found in the response.</div>;
    }

    const headings = data.information.information.headings;
    
    // Function to toggle a heading's expanded state
    const toggleHeading = (heading: string) => {
      const newExpandedHeadings = new Set(expandedHeadings);
      if (expandedHeadings.has(heading)) {
        newExpandedHeadings.delete(heading);
      } else {
        newExpandedHeadings.add(heading);
      }
      setExpandedHeadings(newExpandedHeadings);
    };
    
    return (
      <div className="success-result">
        <h3>Extracted Headings</h3>
        <div className="headings-accordion">
          {Object.entries(headings).map(([heading, description], index) => (
            <div 
              key={index} 
              className={`accordion-item ${expandedHeadings.has(heading) ? 'expanded' : ''}`}
            >
              <button
                className="accordion-header"
                onClick={() => toggleHeading(heading)}
                aria-expanded={expandedHeadings.has(heading)}
              >
                <span className="heading-title">{heading}</span>
                <span className="accordion-icon">
                  {expandedHeadings.has(heading) ? '−' : '+'}
                </span>
              </button>
              <div className="accordion-content">
                <p>{description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Component to display error results
  function ErrorResult({ data }: { data: ErrorResponse }) {
    return (
      <div className="error-result">
        <div className="error-details">
          <div className="error-item">
            <strong>Error:</strong> {data.error}
          </div>
          <div className="error-item">
            <strong>Status Code:</strong> {data.status_code}
          </div>
          
          <div className="error-help">
            <h4>Possible Solutions:</h4>
            <ul>
              {data.status_code === 403 && (
                <li>This website may be blocking web scrapers. Try a different URL.</li>
              )}
              {data.status_code === 404 && (
                <li>The page was not found. Check if the URL is correct.</li>
              )}
              {data.status_code >= 500 && (
                <li>The server encountered an error. Try again later.</li>
              )}
              <li>Check if the website requires authentication.</li>
              <li>Ensure the URL includes the protocol (http:// or https://).</li>
            </ul>
          </div>
        </div>
      </div>
    );
  }

  // Determine button class based on status
  const getButtonClass = () => {
    if (loading) return 'button-loading';
    switch (buttonStatus) {
      case 'success': return 'button-success';
      case 'error': return 'button-error';
      default: return '';
    }
  };

  return (
    <div className="App">
      <button className="back-button" onClick={() => navigate('/')}>
        ← Back to Dashboard
      </button>
      <h1>Content Harvester</h1>
      <form onSubmit={handleSubmit}>
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Enter URL to harvest content"
          required
        />
        <button 
          type="submit" 
          disabled={loading}
          className={getButtonClass()}
        >
          {loading ? 'Harvesting...' : 'Harvest'}
        </button>
      </form>
      
      {error && (
        <div className="error-message">
          <h4>{error}</h4>
        </div>
      )}
      
      {loading && (
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Harvesting content from URL...</p>
        </div>
      )}
      
      {result && (
        <div className="result-container">
          {result.success ? (
            <SuccessResult data={result as SuccessResponse} />
          ) : (
            <ErrorResult data={result as ErrorResponse} />
          )}
        </div>
      )}
    </div>
  );
}

export default App; 