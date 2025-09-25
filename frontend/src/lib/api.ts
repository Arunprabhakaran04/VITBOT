import axios from 'axios';
import { useStore } from './store';

// Create axios instance with base URL
const API_BASE_URL = 'http://127.0.0.1:8000'; // Match the working chatbot-frontend

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const state = useStore.getState();
    if (state.user?.token) {
      config.headers.Authorization = `Bearer ${state.user.token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Auth
export const authAPI = {
  login: async (email: string, password: string) => {
    const response = await api.post('/login', { email, password });
    return response.data;
  },
  
  register: async (email: string, password: string) => {
    const response = await api.post('/register', { email, password });
    return response.data;
  },
  
  logout: async () => {
    const response = await api.post('/logout');
    return response.data;
  },
};

// Chat
export const chatAPI = {
  sendMessage: async (query: string, chatId: string | null, hasPdf: boolean) => {
    const response = await api.post('/chat', { 
      query, 
      chat_id: chatId,
      has_pdf: hasPdf
    });
    return response.data;
  },
  
  listChats: async () => {
    const response = await api.get('/list_chats');
    return response.data.chats;
  },
  
  getChatHistory: async (chatId: string) => {
    const response = await api.get(`/chat_history/${chatId}`);
    return response.data.messages;
  },
  
  deleteChat: async (chatId: string) => {
    const response = await api.delete(`/chat/${chatId}`);
    return response.data;
  },
  
  updateChatTitle: async (chatId: string, title: string) => {
    const response = await api.put(`/chat/${chatId}/title`, { title });
    return response.data;
  },
  
  clearCache: async () => {
    const response = await api.post('/clear_cache');
    return response.data;
  },
  
  clearPdf: async () => {
    const response = await api.post('/clear_pdf');
    return response.data;
  },
};

// PDF
export const pdfAPI = {
  uploadPdf: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/upload_pdf', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
  
  getTaskStatus: async (taskId: string) => {
    const response = await api.get(`/task_status/${taskId}`);
    return response.data;
  },
};

export default api;
