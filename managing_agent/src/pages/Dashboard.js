import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import {
  Typography, Card, CardContent, CardActions, Button, Grid, 
  Chip, CircularProgress, Alert
} from '@mui/material';
import {
  Dns as DnsIcon,
  EventNote as EventNoteIcon
} from '@mui/icons-material';

const Dashboard = () => {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchClients();
    
    // Set up auto refresh every minute
    const intervalId = setInterval(fetchClients, 60000);
    
    // Clean up interval on component unmount
    return () => clearInterval(intervalId);
  }, []);

  // Helper function to check if client is online based on heartbeat
  const isClientOnline = (lastHeartbeat) => {
    if (!lastHeartbeat) return false;
    
    const lastHeartbeatTime = new Date(lastHeartbeat).getTime();
    const currentTime = new Date().getTime();
    const twoMinutesInMs = 2 * 60 * 1000;
    
    // Client is considered online if heartbeat was within last 2 minutes
    return (currentTime - lastHeartbeatTime) < twoMinutesInMs;
  };

  const fetchClients = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/manager/clients/');
      
      // Update client online status based on heartbeat
      const updatedClients = response.data.map(client => ({
        ...client,
        is_online: isClientOnline(client.last_heartbeat)
      }));
      
      setClients(updatedClients);
      setError(null);
    } catch (error) {
      console.error('Error fetching clients:', error);
      setError('Не удалось загрузить список клиентов. Пожалуйста, попробуйте позже.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Grid container spacing={3} alignItems="center" sx={{ mb: 3 }}>
        <Grid item>
          <Typography variant="h4" component="h1">
            Client Dashboard
          </Typography>
        </Grid>
        <Grid item>
          <Button 
            variant="contained" 
            color="primary"
            onClick={fetchClients}
            startIcon={<DnsIcon />}
          >
            Refresh
          </Button>
        </Grid>
      </Grid>

      {loading ? (
        <CircularProgress />
      ) : error ? (
        <Alert severity="error">{error}</Alert>
      ) : clients.length === 0 ? (
        <Alert severity="info">
          Нет подключенных клиентов. Для регистрации клиентов используйте десктопное приложение.
        </Alert>
      ) : (
        <Grid container spacing={3}>
          {clients.map((client) => (
            <Grid item xs={12} sm={6} md={4} key={client.uuid}>
              <Card className="client-card">
                <CardContent>
                  <Typography variant="h6" component="h2">
                    {client.name || 'Unnamed Client'}
                  </Typography>
                  <Typography color="textSecondary">
                    UUID: {client.uuid}
                  </Typography>
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    <Chip
                      label={client.is_online ? 'Online' : 'Offline'}
                      color={client.is_online ? 'success' : 'error'}
                      size="small"
                    />
                  </Typography>
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    Registered: {new Date(client.registered_at).toLocaleString()}
                  </Typography>
                  {client.last_heartbeat && (
                    <Typography variant="body2">
                      Last seen: {new Date(client.last_heartbeat).toLocaleString()}
                    </Typography>
                  )}
                </CardContent>
                <CardActions>
                  <Button 
                    size="small" 
                    component={Link} 
                    to={`/clients/${client.uuid}`}
                    startIcon={<EventNoteIcon />}
                  >
                    View Logs
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
    </div>
  );
};

export default Dashboard; 