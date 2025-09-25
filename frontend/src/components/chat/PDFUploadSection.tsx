import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Upload, 
  FileText, 
  X, 
  CheckCircle, 
  AlertCircle, 
  Loader2,
  Plus,
  Trash2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { useStore } from '@/lib/store';
import { useToast } from '@/hooks/use-toast';
import { pdfAPI, chatAPI } from '@/lib/api';

export const PDFUploadSection = () => {
  const { pdfs, addPDF, updatePDF, removePDF } = useStore();
  const { toast } = useToast();
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    handleFiles(files);
  }, []);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    handleFiles(files);
  }, []);

  const handleFiles = useCallback((files: File[]) => {
    files.forEach(file => {
      if (file.type !== 'application/pdf') {
        toast({
          title: "Invalid file type",
          description: "Please upload PDF files only.",
          variant: "destructive",
        });
        return;
      }

      if (file.size > 10 * 1024 * 1024) { // 10MB limit
        toast({
          title: "File too large",
          description: "Please upload files smaller than 10MB.",
          variant: "destructive",
        });
        return;
      }

      // Remove any existing PDFs first - we only support one PDF at a time in this version
      pdfs.forEach(pdf => {
        removePDF(pdf.id);
      });

      const pdfId = crypto.randomUUID();
      
      // Add PDF to store
      addPDF({
        id: pdfId,
        filename: file.name,
        status: 'uploading',
        progress: 0
      });

      // Upload the file
      uploadFile(pdfId, file);
    });
  }, [addPDF, toast, pdfs, removePDF]);

  const uploadFile = async (pdfId: string, file: File) => {
    try {
      // Simulate upload progress
      const updateProgress = setInterval(() => {
        updatePDF(pdfId, { 
          progress: Math.min((Math.floor(Math.random() * 20) + 1), 100) 
        });
      }, 500);

      // Upload file and get task ID
      const uploadResponse = await pdfAPI.uploadPdf(file);
      const taskId = uploadResponse.task_id;
      
      clearInterval(updateProgress);
      
      // Update status to processing
      updatePDF(pdfId, { 
        status: 'processing', 
        progress: undefined 
      });
      
      // Poll the task status endpoint
      let isComplete = false;
      let attempts = 0;
      const maxAttempts = 180; // 3 minutes with 1 second intervals
      
      while (!isComplete && attempts < maxAttempts) {
        attempts++;
        try {
          const taskStatus = await pdfAPI.getTaskStatus(taskId);
          
          if (taskStatus.status === 'completed') {
            isComplete = true;
            updatePDF(pdfId, { 
              status: 'ready' 
            });
            
            toast({
              title: "PDF processed successfully",
              description: `${file.name} is ready for chat.`,
            });
          } else if (taskStatus.status === 'failed') {
            updatePDF(pdfId, { 
              status: 'error',
              error: taskStatus.message || 'Processing failed'
            });
            
            toast({
              title: "Processing failed",
              description: taskStatus.message || "There was an error processing your PDF.",
              variant: "destructive",
            });
            return;
          } else {
            // Still processing, wait and try again
            await new Promise(resolve => setTimeout(resolve, 1000));
          }
        } catch (error) {
          console.error('Error checking task status:', error);
          // Wait before trying again
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      }
      
      if (!isComplete) {
        // If we've exceeded max attempts
        updatePDF(pdfId, { 
          status: 'error',
          error: 'Processing timed out. Please try again.'
        });
        
        toast({
          title: "Processing timeout",
          description: "PDF processing took too long. Please try uploading again.",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error('Error uploading PDF:', error);
      updatePDF(pdfId, { 
        status: 'error', 
        error: 'Failed to upload the PDF. Please try again.' 
      });
      
      toast({
        title: "Upload failed",
        description: "There was an error uploading your PDF.",
        variant: "destructive",
      });
    }
  };

  const handleRemovePDF = async (pdfId: string) => {
    try {
      // Call the API to clear PDF data
      await chatAPI.clearPdf();
      
      // Remove from UI
      removePDF(pdfId);
      
      toast({
        title: "PDF removed",
        description: "The document has been removed from your collection.",
      });
    } catch (error) {
      console.error('Error removing PDF:', error);
      toast({
        title: "Failed to remove PDF",
        description: "There was an error removing your PDF. Please try again.",
        variant: "destructive",
      });
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'uploading':
        return <Loader2 className="w-4 h-4 animate-spin text-primary" />;
      case 'processing':
        return <Loader2 className="w-4 h-4 animate-spin text-warning" />;
      case 'ready':
        return <CheckCircle className="w-4 h-4 text-success" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-error" />;
      default:
        return <FileText className="w-4 h-4" />;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'uploading':
        return 'Uploading...';
      case 'processing':
        return 'Processing...';
      case 'ready':
        return 'Ready';
      case 'error':
        return 'Error';
      default:
        return 'Unknown';
    }
  };

  return (
    <div className="p-4 space-y-4">
      {/* Upload Area */}
      <motion.div
        className={`
          relative border-2 border-dashed rounded-xl p-6 text-center transition-all duration-300
          ${isDragOver 
            ? 'border-primary bg-primary/5 scale-105' 
            : 'border-border hover:border-primary/50 hover:bg-surface/50'
          }
        `}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        <input
          type="file"
          accept=".pdf"
          multiple
          onChange={handleFileInput}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />
        
        <div className="space-y-3">
          <div className="w-12 h-12 mx-auto rounded-full bg-primary/10 flex items-center justify-center">
            <Upload className="w-6 h-6 text-primary" />
          </div>
          <div>
            <p className="text-sm font-medium text-foreground">
              Drop PDFs here or click to upload
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Max 10MB per file
            </p>
          </div>
        </div>
      </motion.div>

      {/* PDF List */}
      <div className="space-y-2">
        <AnimatePresence>
          {pdfs.map((pdf) => (
            <motion.div
              key={pdf.id}
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="glass rounded-lg p-3"
            >
              <div className="flex items-center space-x-3">
                <div className="flex-shrink-0">
                  {getStatusIcon(pdf.status)}
                </div>
                
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">
                    {pdf.filename}
                  </p>
                  <div className="flex items-center space-x-2 mt-1">
                    <span className="text-xs text-muted-foreground">
                      {getStatusText(pdf.status)}
                    </span>
                    {pdf.progress !== undefined && (
                      <span className="text-xs text-muted-foreground">
                        {pdf.progress}%
                      </span>
                    )}
                  </div>
                  
                  {pdf.progress !== undefined && (
                    <Progress 
                      value={pdf.progress} 
                      className="mt-2 h-1"
                    />
                  )}
                </div>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleRemovePDF(pdf.id)}
                  className="flex-shrink-0 w-6 h-6 p-0 text-muted-foreground hover:text-error"
                >
                  <X className="w-3 h-3" />
                </Button>
              </div>
              
              {pdf.error && (
                <p className="text-xs text-error mt-2">
                  {pdf.error}
                </p>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
        
        {pdfs.length === 0 && (
          <div className="text-center py-6">
            <FileText className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">
              No PDFs uploaded yet
            </p>
          </div>
        )}
      </div>
    </div>
  );
};