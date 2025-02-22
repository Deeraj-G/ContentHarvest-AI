import React, { useState } from 'react';
import './App.css';

function App() {
  const [url, setUrl] = useState('');
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/web_scraper/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `url=${encodeURIComponent(url)}`,
      });
      const data = await response.text();
      setResult(data);
    } catch (error) {
      setResult('Error: Failed to fetch results');
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