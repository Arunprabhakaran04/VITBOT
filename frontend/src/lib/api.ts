import axios from "axios";
import { useStore } from "./store";
import { toast } from "sonner";

// Create axios instance with base URL
const API_BASE_URL = "http://127.0.0.1:8000"; // Match the working chatbot-frontend

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
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

// Add response interceptor to handle token expiration
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const errorMessage =
        error.response?.data?.detail || "Authentication failed";

      // Check if it's a token expiration error (more comprehensive detection)
      const isTokenExpired =
        errorMessage.toLowerCase().includes("expired") ||
        errorMessage.includes("Please login again") ||
        errorMessage.includes("Token has expired");

      if (isTokenExpired) {
        // Show alert for token expiration - stay on current page
        toast.error("Your session has expired. Please login again.", {
          duration: 5000,
          position: "top-center",
          style: {
            backgroundColor: "#fee2e2",
            color: "#991b1b",
            border: "1px solid #fca5a5",
          },
        });

        // Clear only the authentication state without changing the view
        const { setUser } = useStore.getState();
        setUser(null);
      } else {
        // Show generic unauthorized message
        toast.error("Please login to continue", {
          duration: 5000,
          position: "top-center",
        });

        // Clear authentication state for other auth errors too
        const state = useStore.getState();
        useStore.setState({
          user: null,
          isAuthenticated: false,
          // Keep the currentView as is
        });
      }
    } else if (error.response?.status === 403) {
      // Handle forbidden access
      toast.error("Access denied. Insufficient permissions.", {
        duration: 5000,
        position: "top-center",
      });
    } else if (
      error.code === "ECONNABORTED" ||
      error.message === "Network Error"
    ) {
      // Handle network errors
      toast.error("Network error. Please check your connection.", {
        duration: 5000,
        position: "top-center",
      });
    }

    return Promise.reject(error);
  }
);

// Auth
export const authAPI = {
  login: async (email: string, password: string) => {
    const response = await api.post("/login", { email, password });
    return response.data;
  },

  register: async (email: string, password: string) => {
    const response = await api.post("/register", { email, password });
    return response.data;
  },

  logout: async () => {
    const response = await api.post("/logout");
    return response.data;
  },
};

// Chat
export const chatAPI = {
  sendMessage: async (
    query: string,
    chatId: string | null,
    hasPdf: boolean
  ) => {
    const response = await api.post("user/chat/chat", {
      query,
      chat_id: chatId,
      has_pdf: hasPdf,
    });
    return response.data;
  },

  listChats: async () => {
    const response = await api.get("user/chat/list_chats");
    return response.data.chats;
  },

  getChatHistory: async (chatId: string) => {
    const response = await api.get(`user/chat/chat_history/${chatId}`);
    return response.data.messages;
  },

  deleteChat: async (chatId: string) => {
    const response = await api.delete(`user/chat/chat/${chatId}`);
    return response.data;
  },

  updateChatTitle: async (chatId: string, title: string) => {
    const response = await api.put(`user/chat/chat/${chatId}/title`, { title });
    return response.data;
  },

  clearCache: async () => {
    const response = await api.post("user/chat/clear_cache");
    return response.data;
  },

  clearPdf: async () => {
    const response = await api.post("user/chat/clear_pdf");
    return response.data;
  },
};

// PDF
export const pdfAPI = {
  uploadPdf: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);

    const response = await api.post("/upload_pdf", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
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

// Admin API
export const adminAPI = {
  // Document Management
  getDocuments: async () => {
    const response = await api.get("/admin/documents");
    return response.data;
  },

  uploadDocument: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);

    const response = await api.post("/admin/documents/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data;
  },

  getDocument: async (documentId: number) => {
    const response = await api.get(`/admin/documents/${documentId}`);
    return response.data;
  },

  deleteDocument: async (documentId: number) => {
    const response = await api.delete(`/admin/documents/${documentId}`);
    return response.data;
  },

  getDocumentsByStatus: async (status: string) => {
    const response = await api.get(`/admin/documents/status/${status}`);
    return response.data;
  },

  // Knowledge Base Management
  getKnowledgeBaseStats: async () => {
    const response = await api.get("/admin/knowledge-base/stats");
    return response.data;
  },

  getVectorStores: async () => {
    const response = await api.get("/admin/vector-stores");
    return response.data;
  },

  rebuildKnowledgeBase: async () => {
    const response = await api.post("/admin/rebuild-knowledge-base");
    return response.data;
  },
};

// Enhanced Chat API with role awareness
export const enhancedChatAPI = {
  getKnowledgeBaseStatus: async () => {
    const response = await api.get("user/chat/knowledge_base_status");
    return response.data;
  },

  getKnowledgeBaseDocuments: async () => {
    const response = await api.get("user/chat/knowledge_base_documents");
    return response.data;
  },
};
