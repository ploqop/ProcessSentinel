import React, { useState, useContext } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import {
  Container, Paper, Typography, TextField, Button, Box, Alert
} from '@mui/material';

const Register = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    // Проверка полей
    if (!username || !password || !confirmPassword) {
      setError('Пожалуйста, заполните все поля');
      setLoading(false);
      return;
    }

    if (password !== confirmPassword) {
      setError('Пароли не совпадают');
      setLoading(false);
      return;
    }

    try {
      const success = await register(username, password);
      if (success) {
        navigate('/');
      } else {
        setError('Ошибка при регистрации. Возможно, имя пользователя уже занято.');
      }
    } catch (error) {
      setError('Ошибка при регистрации. Пожалуйста, попробуйте снова.');
      console.error('Registration error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="xs">
      <Paper elevation={3} className="login-paper">
        <Typography variant="h5" component="h1" gutterBottom>
          Register New Manager
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

          <TextField
            label="Confirm Password"
            type="password"
            variant="outlined"
            fullWidth
            className="form-field"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
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
            {loading ? 'Registering...' : 'Register'}
          </Button>

          <Box mt={2}>
            <Typography variant="body2">
              Already have an account?{' '}
              <Link to="/login">Login</Link>
            </Typography>
          </Box>
        </form>
      </Paper>
    </Container>
  );
};

export default Register; 