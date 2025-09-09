import React, { createContext, useContext, useState } from 'react';

const ClientContext = createContext({});

export const useClient = () => useContext(ClientContext);

export const ClientProvider = ({ children }) => {
  const [client, setClient] = useState({ client_id: '1001' }); // Default for testing

  return (
    <ClientContext.Provider value={{ client }}>
      {children}
    </ClientContext.Provider>
  );
};