import React from 'react';
import { useNavigate } from 'react-router-dom';
import './Dashboard.css';

function Dashboard() {
  const navigate = useNavigate();
  // TODO: In a real app, this would come from configuration or API
  const defaultTenantId = '66efb688-8cd2-4381-9400-31a7b61e6209';

  return (
    <div className="dashboard">
      <h1>Web Scraper Dashboard</h1>
      <div className="dashboard-content">
        <div className="dashboard-card" 
             onClick={() => navigate(`/v1/tenants/${defaultTenantId}/scrape/`)}>
          <h2>Web Scraper Tool</h2>
          <p>Extract data from any website using our scraping tool</p>
        </div>
      </div>
    </div>
  );
}

export default Dashboard; 