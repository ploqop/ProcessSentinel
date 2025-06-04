import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Typography, Paper, Button, TextField, CircularProgress,
  Alert, List, ListItem, ListItemText, ListItemSecondaryAction,
  IconButton, Divider, Box, Tabs, Tab, FormControl, InputLabel,
  Select, MenuItem, Checkbox, FormControlLabel, Chip, Grid
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  RefreshOutlined as RefreshIcon,
  FilterAlt as FilterIcon
} from '@mui/icons-material';

function TabPanel(props) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`blacklist-tabpanel-${index}`}
      aria-labelledby={`blacklist-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

const BlacklistManagement = () => {
  const [policies, setPolicies] = useState([]);
  const [clients, setClients] = useState([]);
  const [selectedClients, setSelectedClients] = useState([]);
  const [newProcess, setNewProcess] = useState('');
  const [selectedClientId, setSelectedClientId] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [tabValue, setTabValue] = useState(0);
  const [applyToAll, setApplyToAll] = useState(false);

  useEffect(() => {
    fetchClients();
    fetchPolicies();
  }, []);

  const fetchClients = async () => {
    try {
      const response = await axios.get('/api/manager/clients/');
      setClients(response.data);
    } catch (error) {
      console.error('Error fetching clients:', error);
      setError('Failed to load clients. Please try again later.');
    }
  };

  const fetchPolicies = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/manager/blacklist/');
      // Фильтруем только активные политики блокировки
      const blacklist = response.data.filter(policy => policy.is_active && policy.action === 'block');
      setPolicies(blacklist);
      setError(null);
    } catch (error) {
      console.error('Error fetching policies:', error);
      setError('Failed to load blacklist policies. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  const fetchClientPolicies = async (clientUuid) => {
    try {
      setLoading(true);
      const response = await axios.get(`/api/manager/${clientUuid}/blacklist/`);
      // Фильтруем только активные политики блокировки
      const blacklist = response.data.filter(policy => policy.is_active && policy.action === 'block');
      setPolicies(blacklist);
      setError(null);
    } catch (error) {
      console.error('Error fetching client policies:', error);
      setError('Failed to load client-specific blacklist. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  const addToBlacklist = async (e) => {
    e.preventDefault();
    if (!newProcess) return;

    setLoading(true);
    try {
      // Если выбраны несколько клиентов для массового добавления
      if (selectedClients.length > 0) {
        // Последовательное добавление в черный список для каждого выбранного клиента
        for (const clientUuid of selectedClients) {
          await axios.post('/api/manager/blacklist/add/', { 
            process_name: newProcess,
            client_uuid: clientUuid
          });
        }
        setSuccessMessage(`Process "${newProcess}" added to blacklist for ${selectedClients.length} selected clients`);
      } 
      // Если выбран один клиент или добавление в общий черный список
      else {
        await axios.post('/api/manager/blacklist/add/', { 
          process_name: newProcess,
          client_uuid: selectedClientId || undefined
        });
        setSuccessMessage(`Process "${newProcess}" added to ${selectedClientId ? 'client' : 'global'} blacklist`);
      }
      
      setNewProcess('');
      setTimeout(() => setSuccessMessage(null), 3000);
      
      // Перезагружаем списки в зависимости от активной вкладки
      if (tabValue === 0) {
        fetchPolicies();
      } else if (selectedClientId) {
        fetchClientPolicies(selectedClientId);
      }
    } catch (error) {
      console.error('Error adding to blacklist:', error);
      setError('Failed to add process to blacklist. Please try again.');
      setTimeout(() => setError(null), 3000);
    } finally {
      setLoading(false);
    }
  };

  const removeFromBlacklist = async (processName, policyId, clientUuid) => {
    setLoading(true);
    try {
      await axios.post('/api/manager/blacklist/remove/', { 
        process_name: processName,
        client_uuid: clientUuid
      });
      setSuccessMessage(`Process "${processName}" removed from blacklist`);
      setTimeout(() => setSuccessMessage(null), 3000);
      
      // Перезагружаем списки в зависимости от активной вкладки
      if (tabValue === 0) {
        fetchPolicies();
      } else if (selectedClientId) {
        fetchClientPolicies(selectedClientId);
      }
    } catch (error) {
      console.error('Error removing from blacklist:', error);
      setError('Failed to remove process from blacklist. Please try again.');
      setTimeout(() => setError(null), 3000);
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
    if (newValue === 0) {
      fetchPolicies();
    } else if (selectedClientId) {
      fetchClientPolicies(selectedClientId);
    } else {
      setPolicies([]);
    }
  };

  const handleClientChange = (event) => {
    const clientId = event.target.value;
    setSelectedClientId(clientId);
    if (clientId && tabValue === 1) {
      fetchClientPolicies(clientId);
    }
  };

  const handleClientSelectionChange = (event) => {
    const clientId = event.target.value;
    setSelectedClients(
      typeof clientId === 'string' ? clientId.split(',') : clientId,
    );
  };

  const handleApplyToAllChange = (event) => {
    setApplyToAll(event.target.checked);
    if (event.target.checked) {
      setSelectedClientId('');
      setSelectedClients([]);
    }
  };

  return (
    <div>
      <Typography variant="h4" component="h1" gutterBottom>
        Blacklist Management
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {successMessage && <Alert severity="success" sx={{ mb: 2 }}>{successMessage}</Alert>}

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="Global Blacklist" />
          <Tab label="Client-Specific Blacklist" />
        </Tabs>
      </Box>

      <TabPanel value={tabValue} index={0}>
        <Paper elevation={3} sx={{ p: 3, mb: 4 }}>
          <Typography variant="h6" gutterBottom>
            Add Process to Global Blacklist
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
          Global Blacklist (Applies to All Clients)
        </Typography>

        {renderPoliciesList(policies, loading, null)}
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <Paper elevation={3} sx={{ p: 3, mb: 4 }}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                Client-Specific Blacklist Management
              </Typography>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel id="client-select-label">Select Client</InputLabel>
                <Select
                  labelId="client-select-label"
                  value={selectedClientId}
                  label="Select Client"
                  onChange={handleClientChange}
                  disabled={applyToAll || loading}
                >
                  <MenuItem value="">
                    <em>Select a client</em>
                  </MenuItem>
                  {clients.map((client) => (
                    <MenuItem key={client.uuid} value={client.uuid}>
                      {client.name || `Client ${client.uuid.substring(0, 8)}`}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle1" gutterBottom>
                Bulk Operations
              </Typography>
              
              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel id="multiple-client-label">Select Multiple Clients</InputLabel>
                <Select
                  labelId="multiple-client-label"
                  multiple
                  value={selectedClients}
                  onChange={handleClientSelectionChange}
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.map((value) => {
                        const client = clients.find(c => c.uuid === value);
                        return (
                          <Chip 
                            key={value} 
                            label={client ? (client.name || `Client ${value.substring(0, 8)}`) : value} 
                          />
                        );
                      })}
                    </Box>
                  )}
                  disabled={applyToAll || loading}
                >
                  {clients.map((client) => (
                    <MenuItem key={client.uuid} value={client.uuid}>
                      {client.name || `Client ${client.uuid.substring(0, 8)}`}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              
              <FormControlLabel
                control={
                  <Checkbox 
                    checked={applyToAll}
                    onChange={handleApplyToAllChange}
                    disabled={loading}
                  />
                }
                label="Apply to all clients"
              />
            </Grid>
            
            <Grid item xs={12}>
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
                  disabled={loading || !newProcess || (!selectedClientId && selectedClients.length === 0 && !applyToAll)}
                >
                  Add to Blacklist
                </Button>
              </form>
            </Grid>
          </Grid>
        </Paper>

        <Typography variant="h6" gutterBottom>
          {selectedClientId ? 'Client Blacklist' : 'Select a client to view its blacklist'}
        </Typography>

        {renderPoliciesList(policies, loading, selectedClientId)}
      </TabPanel>
    </div>
  );

  function renderPoliciesList(policies, loading, clientUuid) {
    return (
      <>
        {loading ? (
          <CircularProgress />
        ) : policies.length === 0 ? (
          <Alert severity="info">Blacklist is empty. Add processes to block them.</Alert>
        ) : (
          <Paper elevation={2}>
            <List>
              {policies.map((policy, index) => (
                <React.Fragment key={policy.id}>
                  <ListItem>
                    <ListItemText
                      primary={policy.process_name}
                      secondary={
                        <>
                          {`Added: ${new Date(policy.created_at).toLocaleString()}`}
                          {policy.client_name && 
                            <Chip 
                              label={policy.client_name || `Client ${policy.client_uuid?.substring(0, 8)}`}
                              size="small" 
                              color="primary" 
                              variant="outlined"
                              sx={{ ml: 1 }}
                            />
                          }
                        </>
                      }
                    />
                    <ListItemSecondaryAction>
                      <IconButton
                        edge="end"
                        aria-label="delete"
                        onClick={() => removeFromBlacklist(policy.process_name, policy.id, policy.client_uuid)}
                        disabled={loading}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </ListItemSecondaryAction>
                  </ListItem>
                  {index < policies.length - 1 && <Divider />}
                </React.Fragment>
              ))}
            </List>
          </Paper>
        )}
        
        <Box mt={3}>
          <Button
            variant="outlined"
            color="primary"
            startIcon={<RefreshIcon />}
            onClick={() => clientUuid ? fetchClientPolicies(clientUuid) : fetchPolicies()}
            disabled={loading}
          >
            Refresh List
          </Button>
        </Box>
      </>
    );
  }
};

export default BlacklistManagement; 