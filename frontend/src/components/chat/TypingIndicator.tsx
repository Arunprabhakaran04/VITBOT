import { motion } from 'framer-motion';
import { Brain } from 'lucide-react';

export const TypingIndicator = () => {
  return (
    <div className="flex justify-start mb-4 px-4">
      <div className="flex items-end space-x-2 max-w-[80%]">
        {/* Avatar */}
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-surface border border-border/30 flex items-center justify-center mr-2">
          <Brain className="w-4 h-4 text-primary" />
        </div>

        {/* Typing Bubble */}
        <motion.div
          className="message-assistant px-4 py-3 rounded-2xl shadow-sm"
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.2 }}
        >
          <div className="flex items-center space-x-1">
            <span className="text-sm text-muted-foreground mr-2">AI is thinking</span>
            <div className="flex space-x-1">
              <motion.div
                className="w-2 h-2 bg-primary rounded-full"
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 0.6, repeat: Infinity, delay: 0 }}
              />
              <motion.div
                className="w-2 h-2 bg-primary rounded-full"
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 0.6, repeat: Infinity, delay: 0.2 }}
              />
              <motion.div
                className="w-2 h-2 bg-primary rounded-full"
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 0.6, repeat: Infinity, delay: 0.4 }}
              />
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
};