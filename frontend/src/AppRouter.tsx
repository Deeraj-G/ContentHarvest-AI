import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import App from './App';
import Dashboard from './components/Dashboard';

function AppRouter() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/v1/tenants/:tenant_id/harvest/" element={<App />} />
      </Routes>
    </Router>
  );
}

export default AppRouter;
