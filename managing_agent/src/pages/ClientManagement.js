import React, { useEffect, useState } from 'react';
import axios from 'axios';

const ClientManagement = () => {
  const [clients, setClients] = useState([]);

  const fetchClients = async () => {
    try {
      const response = await axios.get('/api/manager/clients/');
      setClients(response.data);
    } catch (error) {
      console.error('Error fetching clients:', error);
    }
  };

  const handleDeleteClient = async (clientUuid) => {
    try {
      const response = await axios.delete(`/api/manager/clients/${clientUuid}/delete/`);
      if (response.status === 200) {
        // Обновляем список клиентов
        fetchClients();
      }
    } catch (error) {
      console.error('Error deleting client:', error);
    }
  };

  useEffect(() => {
    fetchClients();
  }, []);

  return (
    <div>
      {/* Render your clients list here */}
    </div>
  );
};

export default ClientManagement; 