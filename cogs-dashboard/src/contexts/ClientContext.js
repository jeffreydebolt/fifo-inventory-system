import React, { createContext, useContext, useState, useEffect } from 'react';

const ClientContext = createContext({});

export const useClient = () => {
  const context = useContext(ClientContext);
  if (!context) {
    throw new Error('useClient must be used within ClientProvider');
  }
  return context;
};

export const ClientProvider = ({ children }) => {
  const [client, setClient] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for existing session
    const storedClient = localStorage.getItem('fifo_client');
    if (storedClient) {
      try {
        const clientData = JSON.parse(storedClient);
        setClient(clientData);
      } catch (e) {
        localStorage.removeItem('fifo_client');
      }
    }
    setLoading(false);
  }, []);

  const login = async (clientId, password) => {
    // Demo: Simple credential check (for beta deployment)
    const demoClients = {
      'acme_corp': { password: 'test123', company_name: 'Acme Corp', email: 'test1@acme.com' },
      'beta_industries': { password: 'test456', company_name: 'Beta Industries', email: 'test2@beta.com' },
      '1001': { password: 'client1001', company_name: 'FirstLot Client 1001', email: 'client1001@firstlot.co' }
    };
    
    const clientData = demoClients[clientId];
    
    if (clientData && password === clientData.password) {
      const loginData = {
        client_id: clientId,
        company_name: clientData.company_name,
        email: clientData.email
      };
      setClient(loginData);
      localStorage.setItem('fifo_client', JSON.stringify(loginData));
      return { success: true };
    }
    
    return { success: false, error: 'Invalid credentials' };
  };

  const logout = () => {
    setClient(null);
    localStorage.removeItem('fifo_client');
  };

  const value = {
    client,
    login,
    logout,
    loading,
    isAuthenticated: !!client
  };

  return (
    <ClientContext.Provider value={value}>
      {children}
    </ClientContext.Provider>
  );
};

