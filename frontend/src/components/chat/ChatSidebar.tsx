import { motion } from 'framer-motion';
import { useState } from 'react';
import { 
  Brain, 
  Plus, 
  Settings, 
  LogOut, 
  Upload,
  Menu,
  X,
  User,
  FileText,
  MessageSquare
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useStore } from '@/lib/store';
import { PDFUploadSection } from './PDFUploadSection';
import { ChatList } from './ChatList';
import { useIsMobile } from '@/hooks/use-mobile';
import { authAPI } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

export const ChatSidebar = () => {
  const { user, logout, sidebarOpen, setSidebarOpen, setCurrentChatId, setMessages } = useStore();
  const [activeSection, setActiveSection] = useState<'chats' | 'pdfs'>('chats');
  const [isLoading, setIsLoading] = useState(false);
  const isMobile = useIsMobile();
  const { toast } = useToast();

  const handleNewChat = () => {
    // Generate a new chat ID and clear messages to start a new conversation
    const newChatId = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
    setCurrentChatId(newChatId);
    setMessages([]);
    // Switch to chat section
    setActiveSection('chats');
  };
  
  const handleLogout = async () => {
    setIsLoading(true);
    
    try {
      // Call the real API endpoint
      await authAPI.logout();
      
      // Clear local state
      logout();
      
      toast({
        title: "Logged out",
        description: "You have been successfully logged out.",
      });
    } catch (error) {
      console.error('Logout error:', error);
      
      // Still logout locally even if API call fails
      logout();
      
      toast({
        title: "Logout issue",
        description: "There was an issue with the logout process, but you've been logged out of this device.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col bg-surface/50 backdrop-blur-xl">
      {/* Header */}
      <div className="p-4 border-b border-border/30">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <Brain className="w-6 h-6 text-primary" />
            <span className="font-semibold text-foreground">SAGE</span>
          </div>
          {isMobile && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSidebarOpen(false)}
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="w-4 h-4" />
            </Button>
          )}
        </div>

        {/* New Chat Button */}
        <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
          <Button
            onClick={handleNewChat}
            className="w-full gradient-primary text-white hover:shadow-glow transition-all duration-300"
          >
            <Plus className="w-4 h-4 mr-2" />
            New Chat
          </Button>
        </motion.div>
      </div>

      {/* Section Tabs */}
      <div className="px-4 py-2">
        <div className="flex bg-surface rounded-lg p-1">
          <button
            onClick={() => setActiveSection('chats')}
            className={`flex-1 flex items-center justify-center py-2 px-3 rounded-md text-sm font-medium transition-all duration-200 ${
              activeSection === 'chats'
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <MessageSquare className="w-4 h-4 mr-2" />
            Chats
          </button>
          <button
            onClick={() => setActiveSection('pdfs')}
            className={`flex-1 flex items-center justify-center py-2 px-3 rounded-md text-sm font-medium transition-all duration-200 ${
              activeSection === 'pdfs'
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <FileText className="w-4 h-4 mr-2" />
            PDFs
          </button>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-hidden">
        {activeSection === 'chats' ? (
          <ChatList />
        ) : (
          <PDFUploadSection />
        )}
      </div>

      {/* User Section */}
      <div className="p-4 border-t border-border/30">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-full bg-gradient-primary flex items-center justify-center">
              <User className="w-4 h-4 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate">
                {user?.email}
              </p>
              <p className="text-xs text-muted-foreground">
                Premium Plan
              </p>
            </div>
          </div>
          <div className="flex space-x-1">
            <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
              <Settings className="w-4 h-4" />
            </Button>
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={handleLogout}
              disabled={isLoading}
              className="text-muted-foreground hover:text-error"
            >
              {isLoading ? (
                <div className="w-4 h-4 border-2 border-muted-foreground/30 border-t-muted-foreground rounded-full animate-spin" />
              ) : (
                <LogOut className="w-4 h-4" />
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};