import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';
import { MessageSquare, Trash2, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useStore } from '@/lib/store';
import { chatAPI } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

export const ChatList = () => {
  const { chats, setChats, currentChatId, setCurrentChatId, setMessages } = useStore();
  const [hoveredChat, setHoveredChat] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { toast } = useToast();

  // Fetch chats on component mount
  useEffect(() => {
    fetchChats();
  }, []);
  
  const fetchChats = async () => {
    setIsLoading(true);
    try {
      const chatList = await chatAPI.listChats();
      setChats(chatList);
    } catch (error) {
      console.error('Error fetching chats:', error);
      toast({
        title: "Failed to load chats",
        description: "There was an error loading your chat history.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleChatClick = async (chatId: string) => {
    setCurrentChatId(chatId);
    
    try {
      const response = await chatAPI.getChatHistory(chatId);
      // Transform backend message format to frontend format
      const formattedMessages = response.map((msg: any) => ({
        id: crypto.randomUUID(),
        role: msg.role,
        content: msg.content,
        timestamp: new Date().toISOString(),
        is_rag: msg.source === 'rag',
        sources: msg.sources || []
      }));
      setMessages(formattedMessages);
    } catch (error) {
      console.error('Error fetching chat history:', error);
      toast({
        title: "Failed to load chat",
        description: "There was an error loading this conversation.",
        variant: "destructive",
      });
    }
  };

  const handleDeleteChat = async (chatId: string) => {
    try {
      await chatAPI.deleteChat(chatId);
      
      // Update UI
      setChats(chats.filter(chat => chat.chat_id !== chatId));
      
      // If the deleted chat was selected, clear the current chat
      if (currentChatId === chatId) {
        setCurrentChatId(null);
        setMessages([]);
      }
      
      toast({
        title: "Chat deleted",
        description: "The conversation has been deleted.",
      });
    } catch (error) {
      console.error('Error deleting chat:', error);
      toast({
        title: "Failed to delete chat",
        description: "There was an error deleting this conversation.",
        variant: "destructive",
      });
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
    
    if (diffInDays === 0) return 'Today';
    if (diffInDays === 1) return 'Yesterday';
    if (diffInDays < 7) return `${diffInDays} days ago`;
    return date.toLocaleDateString();
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-40">
        <Loader2 className="w-6 h-6 text-primary animate-spin" />
        <span className="ml-2 text-sm text-muted-foreground">Loading chats...</span>
      </div>
    );
  }

  if (chats.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="p-4 text-center">
          <MessageSquare className="w-12 h-12 text-muted-foreground mx-auto mb-3" />
          <p className="text-muted-foreground text-sm">
            No chats yet. Start a new conversation!
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="h-full flex flex-col">
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {chats.map((chat, index) => (
            <motion.div
              key={chat.chat_id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              onHoverStart={() => setHoveredChat(chat.chat_id)}
              onHoverEnd={() => setHoveredChat(null)}
              className={`
                group relative p-3 rounded-lg cursor-pointer transition-all duration-200
                ${currentChatId === chat.chat_id 
                  ? 'bg-primary/10 border border-primary/20' 
                  : 'hover:bg-surface/80'
                }
              `}
              onClick={() => handleChatClick(chat.chat_id)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <h3 className={`
                    font-medium text-sm truncate
                    ${currentChatId === chat.chat_id ? 'text-primary' : 'text-foreground'}
                  `}>
                    {chat.title}
                  </h3>
                  <div className="flex items-center space-x-2 mt-1">
                    <span className="text-xs text-muted-foreground">
                      {formatDate(chat.created_at)}
                    </span>
                    {chat.message_count && (
                      <span className="text-xs text-muted-foreground">
                        • {chat.message_count} messages
                      </span>
                    )}
                  </div>
                </div>

                {hoveredChat === chat.chat_id && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="ml-2"
                  >
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (window.confirm('Are you sure you want to delete this chat?')) {
                          handleDeleteChat(chat.chat_id);
                        }
                      }}
                      className="w-6 h-6 p-0 text-muted-foreground hover:text-error"
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </motion.div>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </>
  );
};