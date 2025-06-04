import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  Typography, Paper, Button, CircularProgress, Alert, Box, Divider, Tabs, Tab,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField,
  List, ListItem, ListItemText, ListItemSecondaryAction, IconButton, Chip,
  Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle
} from '@mui/material';
import { 
  ArrowBack as ArrowBackIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  DeleteForever as DeleteForeverIcon
} from '@mui/icons-material';

function TabPanel(props) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`client-tabpanel-${index}`}
      aria-labelledby={`client-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box p={3}>
          {children}
        </Box>
      )}
    </div>
  );
}

const ClientDetail = () => {
  const { clientUuid } = useParams();
  const navigate = useNavigate();
  const [client, setClient] = useState(null);
  const [violations, setViolations] = useState([]);
  const [blacklist, setBlacklist] = useState([]);
  const [newProcess, setNewProcess] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [tabValue, setTabValue] = useState(0);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    fetchClientData();
    
    // Set up auto refresh every minute
    const intervalId = setInterval(fetchClientData, 60000);
    
    // Clean up interval on component unmount
    return () => clearInterval(intervalId);
  }, [clientUuid]);

  // Helper function to check if client is online based on heartbeat
  const isClientOnline = (lastHeartbeat) => {
    if (!lastHeartbeat) return false;
    
    const lastHeartbeatTime = new Date(lastHeartbeat).getTime();
    const currentTime = new Date().getTime();
    const twoMinutesInMs = 2 * 60 * 1000;
    
    // Client is considered online if heartbeat was within last 2 minutes
    return (currentTime - lastHeartbeatTime) < twoMinutesInMs;
  };

  const fetchClientData = async () => {
    try {
      setLoading(true);
      
      // Получаем информацию о клиенте
      const clientResponse = await axios.get(`/api/manager/clients/${clientUuid}/`);
      
      // Update client online status based on heartbeat
      const clientData = {
        ...clientResponse.data,
        is_online: isClientOnline(clientResponse.data.last_heartbeat)
      };
      setClient(clientData);
      
      // Получаем логи нарушений
      const violationsResponse = await axios.get(`/api/manager/clients/${clientUuid}/logs/`);
      setViolations(violationsResponse.data);
      
      // Получаем чёрный список клиента
      const blacklistResponse = await axios.get(`/api/manager/clients/${clientUuid}/policy/`);
      setBlacklist(blacklistResponse.data.blacklist || []);
      
      setError(null);
    } catch (error) {
      console.error('Error fetching client data:', error);
      setError('Не удалось загрузить данные клиента. Пожалуйста, попробуйте позже.');
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  const addToBlacklist = async (e) => {
    e.preventDefault();
    if (!newProcess) return;

    try {
      setLoading(true);
      await axios.post('/api/manager/blacklist/add/', { 
        process_name: newProcess,
        client_uuid: clientUuid
      });
      
      setNewProcess('');
      setSuccessMessage(`Process "${newProcess}" added to client's blacklist`);
      setTimeout(() => setSuccessMessage(null), 3000);
      
      // Обновляем чёрный список
      const blacklistResponse = await axios.get(`/api/manager/clients/${clientUuid}/policy/`);
      setBlacklist(blacklistResponse.data.blacklist || []);
    } catch (error) {
      console.error('Error adding to blacklist:', error);
      setError('Failed to add process to blacklist. Please try again.');
      setTimeout(() => setError(null), 3000);
    } finally {
      setLoading(false);
    }
  };

  const removeFromBlacklist = async (processName, clientUuid) => {
    try {
      setLoading(true);
      await axios.post('/api/manager/blacklist/remove/', { 
        process_name: processName,
        client_uuid: clientUuid
      });
      
      setSuccessMessage(`Process "${processName}" removed from blacklist`);
      setTimeout(() => setSuccessMessage(null), 3000);
      
      // Обновляем чёрный список
      const blacklistResponse = await axios.get(`/api/manager/clients/${clientUuid}/policy/`);
      setBlacklist(blacklistResponse.data.blacklist || []);
    } catch (error) {
      console.error('Error removing from blacklist:', error);
      setError('Failed to remove process from blacklist. Please try again.');
      setTimeout(() => setError(null), 3000);
    } finally {
      setLoading(false);
    }
  };

  const openDeleteDialog = () => {
    setDeleteDialogOpen(true);
  };

  const closeDeleteDialog = () => {
    setDeleteDialogOpen(false);
  };

  const handleDeleteClient = async () => {
    try {
      setDeleting(true);
      const response = await axios.delete(`/api/manager/clients/${clientUuid}/delete/`);
      
      setSuccessMessage(response.data.message || 'Client deleted successfully');
      closeDeleteDialog();
      
      // Redirect back to dashboard after brief delay
      setTimeout(() => {
        navigate('/');
      }, 1500);
    } catch (error) {
      console.error('Error deleting client:', error);
      setError(error.response?.data?.error || 'Failed to delete client. Please try again.');
      closeDeleteDialog();
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Button
          component={Link}
          to="/"
          startIcon={<ArrowBackIcon />}
        >
          Back to Dashboard
        </Button>
        
        <Button 
          variant="contained" 
          color="error" 
          startIcon={<DeleteForeverIcon />}
          onClick={openDeleteDialog}
        >
          Delete Client
        </Button>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {successMessage && <Alert severity="success" sx={{ mb: 2 }}>{successMessage}</Alert>}

      {loading && !client ? (
        <CircularProgress />
      ) : error && !client ? (
        <Alert severity="error">{error}</Alert>
      ) : client ? (
        <>
          <Typography variant="h4" component="h1" gutterBottom>
            Client: {client.name || 'Unnamed Client'}
          </Typography>
          
          <Box sx={{ mb: 3 }}>
            <Typography variant="body1">
              <strong>UUID:</strong> {client.uuid}
            </Typography>
            <Typography variant="body1" sx={{ display: 'flex', alignItems: 'center', my: 1 }}>
              <strong style={{ marginRight: '8px' }}>Status:</strong>
              <Chip
                label={client.is_online ? 'Online' : 'Offline'}
                color={client.is_online ? 'success' : 'error'}
                size="small"
              />
            </Typography>
            <Typography variant="body1">
              <strong>Registered:</strong> {new Date(client.registered_at).toLocaleString()}
            </Typography>
            {client.last_heartbeat && (
              <Typography variant="body1">
                <strong>Last seen:</strong> {new Date(client.last_heartbeat).toLocaleString()}
              </Typography>
            )}
          </Box>

          <Divider sx={{ my: 3 }} />

          <Box sx={{ width: '100%' }}>
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
              <Tabs value={tabValue} onChange={handleTabChange} aria-label="client tabs">
                <Tab label="Violation Logs" />
                <Tab label="Blacklist" />
              </Tabs>
            </Box>
            
            <TabPanel value={tabValue} index={0}>
              {violations.length === 0 ? (
                <Alert severity="info">No violation logs found for this client</Alert>
              ) : (
                <TableContainer component={Paper}>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Timestamp</TableCell>
                        <TableCell>Process</TableCell>
                        <TableCell>PID</TableCell>
                        <TableCell>Event</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {violations.map((log) => (
                        <TableRow key={log.id}>
                          <TableCell>
                            {new Date(log.timestamp).toLocaleString()}
                          </TableCell>
                          <TableCell>
                            {log.data.process_name}
                          </TableCell>
                          <TableCell>
                            {log.data.pid}
                          </TableCell>
                          <TableCell>
                            {log.event}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </TabPanel>

            <TabPanel value={tabValue} index={1}>
              <Paper elevation={3} sx={{ p: 3, mb: 4 }}>
                <Typography variant="h6" gutterBottom>
                  Add Process to Client's Blacklist
                </Typography>
                <form onSubmit={addToBlacklist} style={{ display: 'flex', alignItems: 'flex-start' }}>
                  <TextField
                    label="Process Name"
                    placeholder="e.g., notepad.exe"
                    value={newProcess}
                    onChange={(e) => setNewProcess(e.target.value)}
                    fullWidth
                    sx={{ mr: 2 }}
                    disabled={loading}
                  />
                  <Button
                    type="submit"
                    variant="contained"
                    color="primary"
                    startIcon={<AddIcon />}
                    disabled={loading || !newProcess}
                  >
                    Add
                  </Button>
                </form>
              </Paper>

              <Typography variant="h6" gutterBottom>
                Client's Blacklist
              </Typography>

              {loading ? (
                <CircularProgress />
              ) : blacklist.length === 0 ? (
                <Alert severity="info">This client has no specific blacklist entries. It uses the global blacklist.</Alert>
              ) : (
                <Paper elevation={2}>
                  <List>
                    {blacklist.map((policy, index) => (
                      <React.Fragment key={policy.id}>
                        <ListItem>
                          <ListItemText
                            primary={policy.process_name}
                            secondary={`Added: ${new Date(policy.created_at).toLocaleString()}`}
                          />
                          <ListItemSecondaryAction>
                            <IconButton
                              edge="end"
                              aria-label="delete"
                              onClick={() => removeFromBlacklist(policy.process_name, policy.client_uuid)}
                              disabled={loading}
                            >
                              <DeleteIcon />
                            </IconButton>
                          </ListItemSecondaryAction>
                        </ListItem>
                        {index < blacklist.length - 1 && <Divider />}
                      </React.Fragment>
                    ))}
                  </List>
                </Paper>
              )}
              
              <Box mt={3}>
                <Button
                  variant="outlined"
                  color="primary"
                  onClick={fetchClientData}
                  disabled={loading}
                >
                  Refresh List
                </Button>
              </Box>
            </TabPanel>
          </Box>
        </>
      ) : (
        <Alert severity="error">Client not found</Alert>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={closeDeleteDialog}
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
      >
        <DialogTitle id="alert-dialog-title">
          {"Delete Client?"}
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="alert-dialog-description">
            Are you sure you want to delete this client? This action cannot be undone.
            All policies and logs associated with this client will also be deleted.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeDeleteDialog} disabled={deleting}>
            Cancel
          </Button>
          <Button 
            onClick={handleDeleteClient} 
            color="error" 
            variant="contained"
            disabled={deleting}
            startIcon={deleting ? <CircularProgress size={20} /> : <DeleteForeverIcon />}
            autoFocus
          >
            {deleting ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};

export default ClientDetail; 