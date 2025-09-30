import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useStore } from '@/lib/store';
import { AuthContainer } from '@/components/auth/AuthContainer';
import { ChatLayout } from '@/components/chat/ChatLayout';

const Index = () => {
  const { currentView, isAuthenticated, user, setCurrentView } = useStore();
  const navigate = useNavigate();

  useEffect(() => {
    // Set initial view based on authentication status
    if (isAuthenticated) {
      // Redirect admin users to admin dashboard
      if (user?.role === 'admin') {
        navigate('/admin');
        return;
      }
      setCurrentView('chat');
    } else {
      setCurrentView('auth');
    }
  }, [isAuthenticated, user, setCurrentView, navigate]);

  return (
    <div className="h-screen bg-background">
      <motion.div
        key={currentView}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.3 }}
        className="h-full"
      >
        {currentView === 'auth' ? <AuthContainer /> : <ChatLayout />}
      </motion.div>
    </div>
  );
};

export default Index;
