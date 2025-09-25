import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  email: string;
  token: string;
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

interface AppState {
  // Auth
  user: User | null;
  isAuthenticated: boolean;
  
  // UI State
  currentView: 'auth' | 'chat';
  sidebarOpen: boolean;
  isLoading: boolean;
  
  // Chat
  currentChatId: string | null;
  chats: Chat[];
  messages: Message[];
  messageInput: string;
  isTyping: boolean;
  
  // PDF
  pdfs: PDFStatus[];
  
  // Actions
  setUser: (user: User | null) => void;
  setCurrentView: (view: 'auth' | 'chat') => void;
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
      
      // PDF
      pdfs: [],
      
      // Actions
      setUser: (user) => set({ 
        user, 
        isAuthenticated: !!user,
        currentView: user ? 'chat' : 'auth'
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
      
      logout: () => set({
        user: null,
        isAuthenticated: false,
        currentView: 'auth',
        currentChatId: null,
        chats: [],
        messages: [],
        pdfs: [],
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