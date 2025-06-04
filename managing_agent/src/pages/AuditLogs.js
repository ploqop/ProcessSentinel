import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Paper, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, TextField, Button,
  FormControl, InputLabel, MenuItem, Select, Grid,
  IconButton, CircularProgress, Chip, Tooltip, Alert
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import FilterListIcon from '@mui/icons-material/FilterList';
import RefreshIcon from '@mui/icons-material/Refresh';
import DownloadIcon from '@mui/icons-material/Download';
import ClearIcon from '@mui/icons-material/Clear';
import axios from 'axios';
import format from 'date-fns/format';

const LOG_TYPES = [
  { value: 'client_registration', label: 'Регистрация клиента' },
  { value: 'client_connection', label: 'Подключение клиента' },
  { value: 'client_disconnection', label: 'Отключение клиента' },
  { value: 'policy_update', label: 'Обновление политики' },
  { value: 'policy_violation', label: 'Нарушение политики' },
  { value: 'command_sent', label: 'Отправка команды' },
  { value: 'command_executed', label: 'Выполнение команды' },
  { value: 'login_attempt', label: 'Попытка входа' },
  { value: 'manager_registration', label: 'Регистрация менеджера' },
  { value: 'client_deletion', label: 'Удаление клиента' },
  { value: 'heartbeat', label: 'Сигнал активности' },
  { value: 'error', label: 'Ошибка' }
];

function AuditLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Фильтры
  const [clientUuid, setClientUuid] = useState('');
  const [logType, setLogType] = useState('');
  const [startDate, setStartDate] = useState(null);
  const [endDate, setEndDate] = useState(null);
  const [limit, setLimit] = useState(100);
  const [showFilters, setShowFilters] = useState(false);
  
  // Список клиентов для фильтра
  const [clients, setClients] = useState([]);
  
  useEffect(() => {
    // Загружаем список клиентов
    fetchClients();
    
    // Загружаем логи без фильтров при первой загрузке
    fetchLogs();
  }, []);
  
  const fetchClients = async () => {
    try {
      const response = await axios.get('/api/manager/clients/');
      setClients(response.data);
    } catch (err) {
      console.error('Error fetching clients:', err);
    }
  };
  
  const fetchLogs = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Формируем параметры запроса
      const params = { limit };
      if (clientUuid) params.client_uuid = clientUuid;
      if (logType) params.log_type = logType;
      if (startDate) params.start_date = format(startDate, "yyyy-MM-dd'T'HH:mm:ss");
      if (endDate) params.end_date = format(endDate, "yyyy-MM-dd'T'HH:mm:ss");
      
      const response = await axios.get('/api/audit/logs/', { params });
      setLogs(response.data);
    } catch (err) {
      console.error('Error fetching audit logs:', err);
      setError(err.response?.data?.error || 'Failed to fetch audit logs');
    } finally {
      setLoading(false);
    }
  };
  
  const handleFilterApply = () => {
    fetchLogs();
  };
  
  const handleFilterClear = () => {
    setClientUuid('');
    setLogType('');
    setStartDate(null);
    setEndDate(null);
    setLimit(100);
  };
  
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'N/A';
    try {
      return new Date(timestamp).toLocaleString();
    } catch (e) {
      return timestamp;
    }
  };
  
  const getLogTypeLabel = (type) => {
    const logType = LOG_TYPES.find(lt => lt.value === type);
    return logType ? logType.label : type;
  };
  
  const getChipColor = (logType) => {
    switch (logType) {
      case 'policy_violation':
        return 'error';
      case 'error':
        return 'error';
      case 'client_registration':
        return 'success';
      case 'command_executed':
        return 'info';
      case 'policy_update':
        return 'warning';
      default:
        return 'default';
    }
  };
  
  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Журнал аудита
      </Typography>
      
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between' }}>
        <Button
          startIcon={<FilterListIcon />}
          onClick={() => setShowFilters(!showFilters)}
          variant="outlined"
        >
          {showFilters ? 'Скрыть фильтры' : 'Показать фильтры'}
        </Button>
        
        <Button
          startIcon={<RefreshIcon />}
          onClick={fetchLogs}
          color="primary"
        >
          Обновить
        </Button>
      </Box>
      
      {showFilters && (
        <Paper sx={{ p: 2, mb: 3 }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={6} md={3}>
              <FormControl fullWidth>
                <InputLabel>Клиент</InputLabel>
                <Select
                  value={clientUuid}
                  onChange={(e) => setClientUuid(e.target.value)}
                  label="Клиент"
                >
                  <MenuItem value="">Все клиенты</MenuItem>
                  {clients.map((client) => (
                    <MenuItem key={client.uuid} value={client.uuid}>
                      {client.name || client.uuid}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <FormControl fullWidth>
                <InputLabel>Тип события</InputLabel>
                <Select
                  value={logType}
                  onChange={(e) => setLogType(e.target.value)}
                  label="Тип события"
                >
                  <MenuItem value="">Все типы</MenuItem>
                  {LOG_TYPES.map((type) => (
                    <MenuItem key={type.value} value={type.value}>
                      {type.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <LocalizationProvider dateAdapter={AdapterDateFns}>
              <Grid item xs={12} sm={6} md={2}>
                <DatePicker
                  label="Начало периода"
                  value={startDate}
                  onChange={(date) => setStartDate(date)}
                  renderInput={(params) => <TextField {...params} fullWidth />}
                />
              </Grid>
              
              <Grid item xs={12} sm={6} md={2}>
                <DatePicker
                  label="Конец периода"
                  value={endDate}
                  onChange={(date) => setEndDate(date)}
                  renderInput={(params) => <TextField {...params} fullWidth />}
                />
              </Grid>
            </LocalizationProvider>
            
            <Grid item xs={12} sm={6} md={2}>
              <TextField
                label="Лимит записей"
                type="number"
                value={limit}
                onChange={(e) => setLimit(e.target.value)}
                fullWidth
              />
            </Grid>
            
            <Grid item xs={12} container justifyContent="flex-end" spacing={1}>
              <Grid item>
                <Button 
                  variant="outlined" 
                  color="secondary"
                  startIcon={<ClearIcon />}
                  onClick={handleFilterClear}
                >
                  Сбросить
                </Button>
              </Grid>
              <Grid item>
                <Button 
                  variant="contained" 
                  color="primary"
                  onClick={handleFilterApply}
                >
                  Применить
                </Button>
              </Grid>
            </Grid>
          </Grid>
        </Paper>
      )}
      
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      
      <Paper>
        <TableContainer component={Paper}>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <CircularProgress />
            </Box>
          ) : (
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Время</TableCell>
                  <TableCell>Тип события</TableCell>
                  <TableCell>Клиент</TableCell>
                  <TableCell>Детали</TableCell>
                  <TableCell>IP адрес</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {logs.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} align="center">
                      Нет данных для отображения
                    </TableCell>
                  </TableRow>
                ) : (
                  logs.map((log) => (
                    <TableRow key={log.id}>
                      <TableCell>{formatTimestamp(log.timestamp)}</TableCell>
                      <TableCell>
                        <Chip 
                          label={getLogTypeLabel(log.log_type)} 
                          color={getChipColor(log.log_type)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{log.client_name || 'N/A'}</TableCell>
                      <TableCell>
                        <Tooltip title={JSON.stringify(log.details, null, 2)}>
                          <span>
                            {JSON.stringify(log.details).substring(0, 50)}
                            {JSON.stringify(log.details).length > 50 ? '...' : ''}
                          </span>
                        </Tooltip>
                      </TableCell>
                      <TableCell>{log.ip_address || 'N/A'}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          )}
        </TableContainer>
      </Paper>
    </Box>
  );
}

export default AuditLogs;