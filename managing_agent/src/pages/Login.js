import React, { useState, useContext } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import {
  Container, Paper, Typography, TextField, Button, Box, Alert
} from '@mui/material';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    if (!username || !password) {
      setError('Пожалуйста, заполните все поля');
      setLoading(false);
      return;
    }

    try {
      const success = await login(username, password);
      if (success) {
        navigate('/');
      } else {
        setError('Неверное имя пользователя или пароль');
      }
    } catch (error) {
      setError('Ошибка аутентификации. Пожалуйста, попробуйте снова.');
      console.error('Login error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="xs">
      <Paper elevation={3} className="login-paper">
        <Typography variant="h5" component="h1" gutterBottom>
          Process Sentinel Login
        </Typography>

        {error && <Alert severity="error" className="alert">{error}</Alert>}

        <form onSubmit={handleSubmit}>
          <TextField
            label="Username"
            variant="outlined"
            fullWidth
            className="form-field"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={loading}
          />

          <TextField
            label="Password"
            type="password"
            variant="outlined"
            fullWidth
            className="form-field"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading}
          />

          <Button
            type="submit"
            variant="contained"
            color="primary"
            size="large"
            fullWidth
            className="form-field"
            disabled={loading}
          >
            {loading ? 'Logging in...' : 'Login'}
          </Button>

          <Box mt={2}>
            <Typography variant="body2">
              Don't have an account?{' '}
              <Link to="/register">Register</Link>
            </Typography>
          </Box>
        </form>
      </Paper>
    </Container>
  );
};

export default Login; 