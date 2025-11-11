import { motion } from 'framer-motion';
import { Mic, MicOff, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

export interface VoiceButtonProps {
  isRecording: boolean;
  isTranscribing: boolean;
  onStartRecording: () => void;
  onStopRecording: () => void;
  disabled?: boolean;
}

export const VoiceButton = ({ 
  isRecording, 
  isTranscribing, 
  onStartRecording, 
  onStopRecording,
  disabled 
}: VoiceButtonProps) => {
  const handleClick = () => {
    if (isRecording) {
      onStopRecording();
    } else {
      onStartRecording();
    }
  };

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <motion.div
            whileHover={{ scale: disabled ? 1 : 1.05 }}
            whileTap={{ scale: disabled ? 1 : 0.95 }}
          >
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClick}
              disabled={disabled || isTranscribing}
              className={`flex-shrink-0 transition-all duration-300 ${
                isRecording 
                  ? 'text-red-500 hover:text-red-600 hover:bg-red-50' 
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {isTranscribing ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : isRecording ? (
                <motion.div
                  animate={{
                    scale: [1, 1.2, 1],
                  }}
                  transition={{
                    duration: 1,
                    repeat: Infinity,
                    ease: "easeInOut"
                  }}
                >
                  <MicOff className="w-4 h-4" />
                </motion.div>
              ) : (
                <Mic className="w-4 h-4" />
              )}
            </Button>
          </motion.div>
        </TooltipTrigger>
        <TooltipContent>
          {isTranscribing 
            ? 'Transcribing audio...'
            : isRecording 
              ? 'Click to stop recording' 
              : 'Click to start voice search'
          }
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};
