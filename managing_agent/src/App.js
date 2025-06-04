import React, { useContext } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthContext } from './context/AuthContext';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

// Компоненты
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import ClientDetail from './pages/ClientDetail';
import BlacklistManagement from './pages/BlacklistManagement';
import Layout from './components/Layout';

// Защищенный маршрут
const ProtectedRoute = ({ children }) => {
  const { token, loading } = useContext(AuthContext);

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!token) {
    return <Navigate to="/login" />;
  }

  return children;
};

// Тема Material UI
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/" element={
          <ProtectedRoute>
            <Layout>
              <Dashboard />
            </Layout>
          </ProtectedRoute>
        } />
        <Route path="/clients/:clientUuid" element={
          <ProtectedRoute>
            <Layout>
              <ClientDetail />
            </Layout>
          </ProtectedRoute>
        } />
        <Route path="/blacklist" element={
          <ProtectedRoute>
            <Layout>
              <BlacklistManagement />
            </Layout>
          </ProtectedRoute>
        } />
      </Routes>
    </ThemeProvider>
  );
}

export default App; 