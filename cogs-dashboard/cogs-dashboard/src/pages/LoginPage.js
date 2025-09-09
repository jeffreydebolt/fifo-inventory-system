import React from 'react';

export default function LoginPage() {
  return (
    <div style={{ padding: 20 }}>
      <h1>FIFO COGS Dashboard</h1>
      <button onClick={() => window.location.href = '/upload'}>
        Go to Upload Page
      </button>
    </div>
  );
}