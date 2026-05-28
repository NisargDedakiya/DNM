import React from 'react';
import AppRoutes from './routes';
import { initializeAuthSync } from './realtime/authSync';
import { initializeEventReconciler } from './realtime/eventReconciler';

// Initialize core synchronized operational layers
initializeAuthSync();
initializeEventReconciler();

function App() {
  return (
    <AppRoutes />
  );
}

export default App;
