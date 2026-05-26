import React, { createContext, useContext, useState, useEffect } from 'react';
import apiClient, { ENDPOINTS } from '../api/endpoints'; // Assuming client maps via axios

export const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [org, setOrg] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      // Mock validation / fetch ME
      setUser({ id: 'u1', role: 'admin', name: 'Nisarg' });
      setOrg({ id: 'org_default_1', name: 'NisargHQ' });
      localStorage.setItem('org_id', 'org_default_1');
    }
    setLoading(false);
  }, []);

  const login = (token, orgId) => {
    localStorage.setItem('auth_token', token);
    localStorage.setItem('org_id', orgId);
    setUser({ id: 'u1', role: 'admin' });
    setOrg({ id: orgId });
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('org_id');
    setUser(null);
    setOrg(null);
    window.location.href = '/login';
  };

  return (
    <AuthContext.Provider value={{ user, org, login, logout, loading }}>
      {!loading && children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
