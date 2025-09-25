import { motion } from 'framer-motion';
import { User, Brain, FileText, Clock, AlertCircle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { SourceCitations } from './SourceCitations';

interface Source {
  document: string;
  page: number | string;
  chunk_index?: number;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  is_rag?: boolean;
  sources?: Source[];
}

interface MessageBubbleProps {
  message: Message;
}

export const MessageBubble = ({ message }: MessageBubbleProps) => {
  const isUser = message.role === 'user';
  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`flex max-w-[80%] ${isUser ? 'flex-row-reverse' : 'flex-row'} items-end space-x-2`}>
        {/* Avatar */}
        <motion.div
          className={`
            flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center
            ${isUser ? 'gradient-primary ml-2' : message.is_rag ? 'bg-emerald-800/40 border border-emerald-500/50 mr-2' : 'bg-surface border border-border/30 mr-2'}
          `}
          whileHover={{ scale: 1.1 }}
        >
          {isUser ? (
            <User className="w-4 h-4 text-white" />
          ) : message.is_rag ? (
            <FileText className="w-4 h-4 text-emerald-300" />
          ) : (
            <Brain className="w-4 h-4 text-primary" />
          )}
        </motion.div>

        {/* Message Content */}
        <motion.div
          className={`
            relative px-4 py-3 rounded-2xl shadow-sm
            ${isUser 
              ? 'message-user text-white' 
              : message.is_rag 
                ? 'bg-emerald-900/20 border border-emerald-500/30 text-emerald-100' 
                : 'message-assistant text-foreground'
            }
          `}
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.2 }}
        >
          {/* Source Indicator */}
          {!isUser && (
            <div className="flex items-center space-x-1 mb-2">
              {message.is_rag ? (
                <Badge variant="outline" className="text-xs bg-emerald-800/30 text-emerald-300 border-emerald-500/40">
                  <FileText className="w-3 h-3 mr-1" />
                  PDF Context
                </Badge>
              ) : (
                <Badge variant="outline" className="text-xs bg-purple-50 text-purple-700 border-purple-200">
                  <Brain className="w-3 h-3 mr-1" />
                  General AI
                </Badge>
              )}
            </div>
          )}

          {/* Message Text */}
          <div className="whitespace-pre-wrap leading-relaxed">
            {message.content}
          </div>

          {/* Source Citations for RAG responses */}
          {!isUser && message.is_rag && message.sources && (
            <SourceCitations sources={message.sources} />
          )}

          {/* Timestamp */}
          <div className={`
            flex items-center space-x-1 mt-2 text-xs opacity-70
            ${isUser ? 'text-white/80' : 'text-muted-foreground'}
          `}>
            <Clock className="w-3 h-3" />
            <span>{formatTime(message.timestamp)}</span>
          </div>

          {/* Message Tail */}
          <div className={`
            absolute bottom-0 w-3 h-3
            ${isUser 
              ? 'right-0 translate-x-1 bg-gradient-to-br from-primary to-secondary' 
              : message.is_rag
                ? 'left-0 -translate-x-1 bg-emerald-900/20 border-l border-b border-emerald-500/30'
                : 'left-0 -translate-x-1 bg-surface border-l border-b border-border/30'
            }
            ${isUser ? 'rounded-bl-full' : 'rounded-br-full'}
          `} />
        </motion.div>
      </div>
    </div>
  );
};