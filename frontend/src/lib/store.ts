import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  email: string;
  token: string;
  role: 'user' | 'admin';
}

export interface AdminDocument {
  id: number;
  filename: string;
  original_filename: string;
  file_size?: number;
  processing_status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  status?: 'processed' | 'processing' | 'failed'; // Additional status field for compatibility
  language: string;
  description?: string;
  uploaded_at?: string; // Alternative to created_at
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

interface Chat {
  chat_id: string;
  title: string;
  created_at: string;
  message_count?: number;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  is_rag?: boolean;
  sources?: Array<{
    document: string;
    page: number | string;
    chunk_index?: number;
  }>;
}

interface PDFStatus {
  id: string;
  filename: string;
  status: 'uploading' | 'processing' | 'ready' | 'error';
  progress?: number;
  error?: string;
}

interface KnowledgeBaseStatus {
  available_documents: number;
  total_chunks: number;
  languages: number;
  status: 'active' | 'empty';
  can_upload: boolean;
  can_query: boolean;
}

interface AppState {
  // Auth
  user: User | null;
  isAuthenticated: boolean;
  
  // UI State
  currentView: 'auth' | 'chat' | 'admin';
  sidebarOpen: boolean;
  isLoading: boolean;
  
  // Chat
  currentChatId: string | null;
  chats: Chat[];
  messages: Message[];
  messageInput: string;
  isTyping: boolean;
  
  // PDF (Legacy)
  pdfs: PDFStatus[];
  
  // Admin Documents
  adminDocuments: AdminDocument[];
  knowledgeBaseStatus: KnowledgeBaseStatus | null;
  
  // Actions
  setUser: (user: User | null) => void;
  setCurrentView: (view: 'auth' | 'chat' | 'admin') => void;
  setSidebarOpen: (open: boolean) => void;
  setIsLoading: (loading: boolean) => void;
  setCurrentChatId: (id: string | null) => void;
  setChats: (chats: Chat[]) => void;
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  setMessageInput: (input: string) => void;
  setIsTyping: (typing: boolean) => void;
  addPDF: (pdf: PDFStatus) => void;
  updatePDF: (id: string, updates: Partial<PDFStatus>) => void;
  removePDF: (id: string) => void;
  
  // Admin Actions
  setAdminDocuments: (documents: AdminDocument[]) => void;
  addAdminDocument: (document: AdminDocument) => void;
  updateAdminDocument: (id: number, updates: Partial<AdminDocument>) => void;
  removeAdminDocument: (id: number) => void;
  setKnowledgeBaseStatus: (status: KnowledgeBaseStatus) => void;
  
  logout: () => void;
}

export const useStore = create<AppState>()(
  persist(
    (set, get) => ({
      // Auth
      user: null,
      isAuthenticated: false,
      
      // UI State
      currentView: 'auth',
      sidebarOpen: true,
      isLoading: false,
      
      // Chat
      currentChatId: null,
      chats: [],
      messages: [],
      messageInput: '',
      isTyping: false,
      
      // PDF (Legacy)
      pdfs: [],
      
      // Admin Documents
      adminDocuments: [],
      knowledgeBaseStatus: null,
      
      // Actions
      setUser: (user) => set({ 
        user, 
        isAuthenticated: !!user,
        currentView: user ? (user.role === 'admin' ? 'admin' : 'chat') : 'auth'
      }),
      
      setCurrentView: (view) => set({ currentView: view }),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      setIsLoading: (loading) => set({ isLoading: loading }),
      
      setCurrentChatId: (id) => set({ currentChatId: id }),
      setChats: (chats) => set({ chats }),
      setMessages: (messages) => set({ messages }),
      addMessage: (message) => set((state) => ({ 
        messages: [...state.messages, message] 
      })),
      setMessageInput: (input) => set({ messageInput: input }),
      setIsTyping: (typing) => set({ isTyping: typing }),
      
      // Legacy PDF actions
      addPDF: (pdf) => set((state) => ({ 
        pdfs: [...state.pdfs, pdf] 
      })),
      updatePDF: (id, updates) => set((state) => ({
        pdfs: state.pdfs.map(pdf => 
          pdf.id === id ? { ...pdf, ...updates } : pdf
        )
      })),
      removePDF: (id) => set((state) => ({
        pdfs: state.pdfs.filter(pdf => pdf.id !== id)
      })),
      
      // Admin Document Actions
      setAdminDocuments: (documents) => set({ adminDocuments: documents }),
      addAdminDocument: (document) => set((state) => ({ 
        adminDocuments: [...state.adminDocuments, document] 
      })),
      updateAdminDocument: (id, updates) => set((state) => ({
        adminDocuments: state.adminDocuments.map(doc => 
          doc.id === id ? { ...doc, ...updates } : doc
        )
      })),
      removeAdminDocument: (id) => set((state) => ({
        adminDocuments: state.adminDocuments.filter(doc => doc.id !== id)
      })),
      setKnowledgeBaseStatus: (status) => set({ knowledgeBaseStatus: status }),
      
      logout: () => set({
        user: null,
        isAuthenticated: false,
        currentView: 'auth',
        currentChatId: null,
        chats: [],
        messages: [],
        pdfs: [],
        adminDocuments: [],
        knowledgeBaseStatus: null,
        messageInput: ''
      })
    }),
    {
      name: 'rag-chatbot-storage',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated
      })
    }
  )
);