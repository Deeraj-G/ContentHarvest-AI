import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import './App.css';

function App() {
  const params = useParams<{ tenant_id: string }>();
  console.log("Params:", params);
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
      const response = await fetch(`http://localhost:8000/v1/tenants/${tenant_id}/scrape/`, {
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
      <h1>Web Scraper</h1>
      <form onSubmit={handleSubmit}>
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Enter URL to scrape"
          required
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Scraping...' : 'Scrape'}
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