import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './App.css';

function App() {
  const navigate = useNavigate();
  const params = useParams<{ tenant_id: string }>();
  const tenant_id = params.tenant_id;
  const [url, setUrl] = useState('');
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    if (!tenant_id) {
      setError('Error: Tenant ID is undefined');
      setLoading(false);
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
        throw new Error(data.content.error);
      }
      setResult(JSON.stringify(data.content, null, 2));
    } catch (error) {
      setError(`Error: ${error instanceof Error ? error.message : 'Failed to fetch results'}`);
    }
    setLoading(false);
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
          placeholder="Enter URL to scrape"
          required
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Harvesting...' : 'Harvest'}
        </button>
      </form>
      {error && (
        <div className="error">
          <h4 style={{ color: 'red' }}>{error}</h4>
        </div>
      )}
      {result && (
        <div className="result">
          <h2>Results:</h2>
          <pre>{result}</pre>
        </div>
      )}
    </div>
  );
}

export default App; 