import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { useStore } from '@/lib/store';
import { ChatSidebar } from './ChatSidebar';
import { ChatArea } from './ChatArea';
import { useIsMobile } from '@/hooks/use-mobile';

export const ChatLayout = () => {
  const { sidebarOpen, setSidebarOpen } = useStore();
  const isMobile = useIsMobile();

  // Close sidebar on mobile by default
  useEffect(() => {
    if (isMobile) {
      setSidebarOpen(false);
    }
  }, [isMobile, setSidebarOpen]);

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar Overlay for Mobile */}
      {isMobile && sidebarOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40"
        />
      )}

      {/* Sidebar */}
      <motion.div
        initial={false}
        animate={{
          x: sidebarOpen ? 0 : isMobile ? -320 : -280,
          width: isMobile ? 320 : 280
        }}
        transition={{ type: "spring", stiffness: 400, damping: 30 }}
        className={`
          ${isMobile ? 'fixed' : 'relative'} 
          z-50 h-full glass-strong border-r border-border/30
        `}
      >
        <ChatSidebar />
      </motion.div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <ChatArea />
      </div>

      {/* Background Elements */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden -z-10">
        <div className="absolute top-20 left-1/4 w-96 h-96 gradient-glow rounded-full blur-3xl opacity-5 animate-pulse-glow" />
        <div className="absolute bottom-20 right-1/4 w-96 h-96 gradient-glow rounded-full blur-3xl opacity-5 animate-pulse-glow delay-1000" />
      </div>
    </div>
  );
};