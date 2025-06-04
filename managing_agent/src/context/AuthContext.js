import React, { createContext, useState, useEffect } from 'react';
import axios from 'axios';

export const AuthContext = createContext();

// Set up axios interceptor
axios.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor to handle token expiration
axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // If the error is 401 and we haven't tried to refresh the token yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        const refreshToken = localStorage.getItem('refreshToken');
        if (!refreshToken) {
          throw new Error('No refresh token available');
        }
        
        const response = await axios.post('/api/manager/token/refresh/', {
          refresh: refreshToken
        });
        
        const { access } = response.data;
        localStorage.setItem('token', access);
        
        // Update the original request with the new token
        originalRequest.headers.Authorization = `Bearer ${access}`;
        
        // Retry the original request
        return axios(originalRequest);
      } catch (refreshError) {
        // If refresh token fails, logout the user
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
        localStorage.removeItem('managerUuid');
        localStorage.removeItem('username');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

export const AuthProvider = ({ children }) => {
  const [currentUser, setCurrentUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Проверяем, есть ли JWT в localStorage
    const storedToken = localStorage.getItem('token');
    if (storedToken) {
      setToken(storedToken);
      // Получаем информацию о текущем пользователе
      fetchUserData();
    } else {
      setLoading(false);
    }
  }, []);

  const fetchUserData = async () => {
    try {
      // Fetch manager profile from the server
      const response = await axios.get('/api/manager/profile/');
      const { uuid, username } = response.data;
      
      // Update localStorage and state
      localStorage.setItem('managerUuid', uuid);
      localStorage.setItem('username', username);
      
      setCurrentUser({
        uuid: uuid,
        username: username
      });
      
      setLoading(false);
    } catch (error) {
      console.error('Ошибка при получении данных пользователя:', error);
      logout();
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    try {
      const response = await axios.post('/api/manager/token/', { username, password });
      const { access, refresh } = response.data;
      
      // Сохраняем токены
      localStorage.setItem('token', access);
      localStorage.setItem('refreshToken', refresh);
      
      // Получаем данные менеджера
      const managerResponse = await axios.get('/api/manager/profile/', {
        headers: { 'Authorization': `Bearer ${access}` }
      });
      
      // Сохраняем данные менеджера
      localStorage.setItem('managerUuid', managerResponse.data.uuid);
      localStorage.setItem('username', username);
      
      // Обновляем состояние
      setToken(access);
      setCurrentUser({
        uuid: managerResponse.data.uuid,
        username: username
      });
      
      return true;
    } catch (error) {
      console.error('Ошибка аутентификации:', error);
      return false;
    }
  };

  const register = async (username, password) => {
    try {
      const response = await axios.post('/api/manager/register/', { username, password });
      // После успешной регистрации выполняем вход
      return login(username, password);
    } catch (error) {
      console.error('Ошибка регистрации:', error);
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('managerUuid');
    localStorage.removeItem('username');
    setToken(null);
    setCurrentUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        currentUser,
        token,
        loading,
        login,
        register,
        logout
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}; 