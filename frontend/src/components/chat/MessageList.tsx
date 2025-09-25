import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { MessageBubble } from './MessageBubble';
import { useStore } from '@/lib/store';

export const MessageList = () => {
  const { messages } = useStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isUserScrolling, setIsUserScrolling] = useState(false);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);
  const [showScrollButton, setShowScrollButton] = useState(false);

  const scrollToBottom = (behavior: 'smooth' | 'auto' = 'smooth') => {
    messagesEndRef.current?.scrollIntoView({ behavior });
    setShouldAutoScroll(true);
    setShowScrollButton(false);
  };

  // Check if user is near the bottom
  const handleScroll = () => {
    if (containerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
      setShouldAutoScroll(isNearBottom);
      setShowScrollButton(!isNearBottom && messages.length > 3);
      
      // Detect if user is actively scrolling
      setIsUserScrolling(true);
      setTimeout(() => setIsUserScrolling(false), 150);
    }
  };

  useEffect(() => {
    // Only auto-scroll for new messages if user is near bottom
    if (shouldAutoScroll && !isUserScrolling) {
      scrollToBottom();
    }
  }, [messages]);

  // Force scroll to bottom when starting a new conversation
  useEffect(() => {
    if (messages.length === 1) {
      setShouldAutoScroll(true);
      setTimeout(() => scrollToBottom('auto'), 100);
    }
  }, [messages.length]);

  return (
    <div className="relative h-full flex flex-col">
      <div 
        ref={containerRef}
        className="flex-1 overflow-y-auto overflow-x-hidden p-4 space-y-4 scroll-smooth chat-scroll"
        onScroll={handleScroll}
      >
        <AnimatePresence initial={false}>
          {messages.map((message, index) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3, delay: index * 0.05 }}
            >
              <MessageBubble message={message} />
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </div>
      
      {/* Scroll to Bottom Button */}
      <AnimatePresence>
        {showScrollButton && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="absolute bottom-4 right-4"
          >
            <Button
              onClick={() => scrollToBottom('smooth')}
              className="rounded-full w-10 h-10 p-0 gradient-primary text-white shadow-lg hover:shadow-glow"
            >
              <ChevronDown className="w-4 h-4" />
            </Button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};