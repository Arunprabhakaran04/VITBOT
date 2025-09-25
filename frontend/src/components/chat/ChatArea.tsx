import { motion } from 'framer-motion';
import { useState } from 'react';
import { Menu, Send, Paperclip, MoreVertical, FileText, Brain, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { useStore } from '@/lib/store';
import { MessageList } from './MessageList';
import { TypingIndicator } from './TypingIndicator';
import { useIsMobile } from '@/hooks/use-mobile';
import { chatAPI } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

export const ChatArea = () => {
  const { 
    sidebarOpen, 
    setSidebarOpen, 
    messageInput, 
    setMessageInput, 
    isTyping,
    setIsTyping,
    addMessage,
    messages,
    currentChatId,
    setCurrentChatId,
    pdfs,
    setChats,
    chats,
  } = useStore();
  const isMobile = useIsMobile();
  const [isLoading, setIsLoading] = useState(false);
  
  // Check if user has any PDFs uploaded and they are ready
  const hasPdf = pdfs.length > 0 && pdfs.some(pdf => pdf.status === 'ready');
  
  // Check if any PDFs are still processing
  const hasProcessingPdf = pdfs.length > 0 && pdfs.some(pdf => pdf.status === 'processing');

  const generateChatId = () => {
    return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
  };

  const handleSendMessage = async () => {
    if (!messageInput.trim() || isLoading) return;

    // Generate a new chat ID if none exists
    let chatId = currentChatId;
    if (!chatId) {
      chatId = generateChatId();
      setCurrentChatId(chatId);
    }

    const userMessage = {
      id: crypto.randomUUID(),
      role: 'user' as const,
      content: messageInput.trim(),
      timestamp: new Date().toISOString()
    };

    // Add user message to UI
    addMessage(userMessage);
    setMessageInput('');
    setIsLoading(true);
    setIsTyping(true);

    try {
      // Call the real API endpoint
      const response = await chatAPI.sendMessage(
        userMessage.content, 
        chatId,
        hasPdf
      );
      
      // Add AI response
      const aiMessage = {
        id: crypto.randomUUID(),
        role: 'assistant' as const,
        content: response.response,
        timestamp: new Date().toISOString(),
        is_rag: response.source === 'rag',
        sources: response.sources || []
      };

      addMessage(aiMessage);
      
      // Refresh chat list to show new chat or update existing one
      try {
        const updatedChats = await chatAPI.listChats();
        setChats(updatedChats);
      } catch (error) {
        console.error('Error refreshing chat list:', error);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      
      // Add error message
      addMessage({
        id: crypto.randomUUID(),
        role: 'assistant' as const,
        content: "I'm sorry, I encountered an error while processing your request. Please try again later.",
        timestamp: new Date().toISOString(),
        is_rag: false
      });
    } finally {
      setIsLoading(false);
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex flex-col p-4 border-b border-border/30 bg-surface/30 backdrop-blur-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {(isMobile || !sidebarOpen) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="text-muted-foreground hover:text-foreground"
              >
                <Menu className="w-5 h-5" />
              </Button>
            )}
            <div>
              <h2 className="font-semibold text-foreground">
                SAGE
              </h2>
              <p className="text-sm text-muted-foreground">
                Ask questions about your uploaded documents
              </p>
            </div>
          </div>
          
          <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
            <MoreVertical className="w-4 h-4" />
          </Button>
        </div>
        
        {/* PDF Status Indicator */}
        <div className="mt-2">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                {hasProcessingPdf ? (
                  <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">
                    <AlertCircle className="w-3 h-3 mr-1 animate-pulse" />
                    PDF Processing...
                  </Badge>
                ) : hasPdf ? (
                  <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200">
                    <FileText className="w-3 h-3 mr-1" />
                    PDF Context Active
                  </Badge>
                ) : (
                  <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200">
                    <Brain className="w-3 h-3 mr-1" />
                    General AI Mode
                  </Badge>
                )}
              </TooltipTrigger>
              <TooltipContent>
                {hasProcessingPdf ? 
                  "Your PDF is still processing. Responses will use general AI until processing completes." :
                  hasPdf ? 
                    "Responses will be based on your uploaded PDF documents" : 
                    "No PDFs detected. Responses will use general AI knowledge."
                }
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <motion.div 
              className="text-center max-w-md mx-auto p-6"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
            >
              <div className="w-16 h-16 mx-auto mb-4 gradient-primary rounded-2xl flex items-center justify-center">
                <Send className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-foreground mb-2">
                Start a conversation
              </h3>
              <p className="text-muted-foreground mb-4">
                Upload PDFs and ask questions about your documents. I'll provide answers based on the content.
              </p>
              <div className="space-y-2 text-sm text-muted-foreground">
                <p>• Upload research papers, reports, or any PDF documents</p>
                <p>• Ask specific questions about the content</p>
                <p>• Get AI-powered answers with source references</p>
              </div>
              
              {hasProcessingPdf && (
                <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-sm">
                  <AlertCircle className="w-4 h-4 inline-block mr-1 animate-pulse" />
                  Your PDF is still processing. You can start chatting, but responses will use general AI until processing completes.
                </div>
              )}
            </motion.div>
          </div>
        ) : (
          <MessageList />
        )}
      </div>

      {/* Typing Indicator */}
      {isLoading && <TypingIndicator />}

      {/* Input Area */}
      <div className="p-4 border-t border-border/30 bg-surface/30 backdrop-blur-sm">
        <div className="flex items-end space-x-3">
          <Button 
            variant="ghost" 
            size="sm"
            className="flex-shrink-0 text-muted-foreground hover:text-foreground"
          >
            <Paperclip className="w-4 h-4" />
          </Button>
          
          <div className="flex-1 relative">
            <Textarea
              value={messageInput}
              onChange={(e) => setMessageInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={hasPdf ? "Ask a question about your PDF..." : "Ask a general question..."}
              className="min-h-[44px] max-h-32 resize-none bg-surface border-border focus:border-primary focus:ring-primary/20 pr-12"
              disabled={isLoading}
            />
            
            <motion.div
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="absolute right-2 bottom-2"
            >
              <Button
                onClick={handleSendMessage}
                disabled={!messageInput.trim() || isLoading}
                size="sm"
                className="gradient-primary text-white hover:shadow-glow transition-all duration-300"
              >
                <Send className="w-4 h-4" />
              </Button>
            </motion.div>
          </div>
        </div>
        
        <p className="text-xs text-muted-foreground mt-2 text-center">
          Press Enter to send, Shift+Enter for new line
        </p>
      </div>
    </div>
  );
};