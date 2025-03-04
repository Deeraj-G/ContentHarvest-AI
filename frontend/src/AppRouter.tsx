import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import App from './App';

const AppRouter: React.FC = () => {
  return (
    <Router>
      <Routes>
        <Route path="/v1/tenants/:tenant_id/scrape/" element={<App />} />
      </Routes>
    </Router>
  );
};

export default AppRouter;
