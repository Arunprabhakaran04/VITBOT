import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Upload, 
  FileText, 
  X, 
  CheckCircle, 
  AlertCircle, 
  Loader2,
  Plus,
  Trash2,
  Eye,
  Calendar,
  Database,
  Languages,
  FileIcon,
  Download,
  RefreshCw
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useStore } from '@/lib/store';
import { useToast } from '@/hooks/use-toast';
import { adminAPI, enhancedChatAPI } from '@/lib/api';

interface DocumentUploadTask {
  id: string;
  filename: string;
  status: 'uploading' | 'processing' | 'completed' | 'error';
  progress?: number;
  error?: string;
  document_id?: number;
}

export const AdminDocumentManager = () => {
  const { 
    adminDocuments, 
    knowledgeBaseStatus,
    setAdminDocuments, 
    addAdminDocument, 
    removeAdminDocument,
    setKnowledgeBaseStatus 
  } = useStore();
  
  const { toast } = useToast();
  const [uploadTasks, setUploadTasks] = useState<DocumentUploadTask[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Load documents and knowledge base status on mount
  useEffect(() => {
    loadDocuments();
    loadKnowledgeBaseStatus();
  }, []);

  const loadDocuments = async () => {
    try {
      setIsLoading(true);
      const response = await adminAPI.getDocuments();
      setAdminDocuments(response.documents || []);
    } catch (error) {
      console.error('Error loading documents:', error);
      toast({
        title: "Error loading documents",
        description: "Failed to load document list.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const loadKnowledgeBaseStatus = async () => {
    try {
      const response = await enhancedChatAPI.getKnowledgeBaseStatus();
      setKnowledgeBaseStatus(response);
    } catch (error) {
      console.error('Error loading knowledge base status:', error);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    files.forEach(handleFileUpload);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files) {
      Array.from(files).forEach(handleFileUpload);
    }
    e.target.value = '';
  };

  const handleFileUpload = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      toast({
        title: "Invalid file type",
        description: "Only PDF files are allowed.",
        variant: "destructive",
      });
      return;
    }

    const taskId = crypto.randomUUID();
    const uploadTask: DocumentUploadTask = {
      id: taskId,
      filename: file.name,
      status: 'uploading',
      progress: 0
    };

    setUploadTasks(prev => [...prev, uploadTask]);

    try {
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadTasks(prev => prev.map(task => 
          task.id === taskId 
            ? { ...task, progress: Math.min((task.progress || 0) + Math.random() * 20, 90) }
            : task
        ));
      }, 500);

      const response = await adminAPI.uploadDocument(file);
      
      clearInterval(progressInterval);

      // Update task to processing
      setUploadTasks(prev => prev.map(task => 
        task.id === taskId 
          ? { 
              ...task, 
              status: 'processing', 
              progress: 100, 
              document_id: response.document_id 
            }
          : task
      ));

      // Poll for processing status
      pollDocumentStatus(response.document_id, taskId);

      toast({
        title: "Upload successful",
        description: `${file.name} is now being processed.`,
      });

      // Refresh document list
      loadDocuments();

    } catch (error: any) {
      setUploadTasks(prev => prev.map(task => 
        task.id === taskId 
          ? { ...task, status: 'error', error: error.response?.data?.detail || 'Upload failed' }
          : task
      ));

      toast({
        title: "Upload failed",
        description: error.response?.data?.detail || "There was an error uploading your document.",
        variant: "destructive",
      });
    }
  };

  const pollDocumentStatus = async (documentId: number, taskId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const document = await adminAPI.getDocument(documentId);
        
        if (document.processing_status === 'completed') {
          setUploadTasks(prev => prev.map(task => 
            task.id === taskId 
              ? { ...task, status: 'completed' }
              : task
          ));
          
          // Remove task after delay
          setTimeout(() => {
            setUploadTasks(prev => prev.filter(task => task.id !== taskId));
          }, 3000);
          
          clearInterval(pollInterval);
          loadDocuments();
          loadKnowledgeBaseStatus();
          
        } else if (document.processing_status === 'failed') {
          setUploadTasks(prev => prev.map(task => 
            task.id === taskId 
              ? { ...task, status: 'error', error: 'Processing failed' }
              : task
          ));
          clearInterval(pollInterval);
        }
      } catch (error) {
        console.error('Error polling document status:', error);
        clearInterval(pollInterval);
      }
    }, 2000);

    // Stop polling after 5 minutes
    setTimeout(() => clearInterval(pollInterval), 300000);
  };

  const handleDeleteDocument = async (documentId: number, filename: string) => {
    if (!confirm(`Are you sure you want to delete "${filename}"?`)) {
      return;
    }

    try {
      await adminAPI.deleteDocument(documentId);
      removeAdminDocument(documentId);
      loadKnowledgeBaseStatus();
      
      toast({
        title: "Document deleted",
        description: `${filename} has been removed from the knowledge base.`,
      });
    } catch (error: any) {
      toast({
        title: "Delete failed",
        description: error.response?.data?.detail || "Failed to delete document.",
        variant: "destructive",
      });
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'uploading':
        return <Loader2 className="w-4 h-4 animate-spin text-blue-500" />;
      case 'processing':
        return <Loader2 className="w-4 h-4 animate-spin text-yellow-500" />;
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <FileText className="w-4 h-4 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants = {
      'pending': 'secondary',
      'processing': 'default',
      'completed': 'default',
      'failed': 'destructive',
      'cancelled': 'outline'
    } as const;

    return (
      <Badge variant={variants[status as keyof typeof variants] || 'secondary'}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </Badge>
    );
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'Unknown size';
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="flex-shrink-0 p-6 border-b border-border/30">
        {/* Header with Stats */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-foreground">Document Management</h2>
            <p className="text-muted-foreground">
              Manage documents in the global knowledge base
            </p>
          </div>
          <Button
            onClick={loadDocuments}
            variant="outline"
            size="sm"
            className="flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </Button>
        </div>

        {/* Knowledge Base Stats */}
        {knowledgeBaseStatus && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <Database className="w-5 h-5 text-blue-500" />
                  <div>
                    <p className="text-sm font-medium">Documents</p>
                    <p className="text-2xl font-bold">{knowledgeBaseStatus.available_documents}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <FileIcon className="w-5 h-5 text-green-500" />
                  <div>
                    <p className="text-sm font-medium">Text Chunks</p>
                    <p className="text-2xl font-bold">{knowledgeBaseStatus.total_chunks}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <Languages className="w-5 h-5 text-purple-500" />
                <div>
                  <p className="text-sm font-medium">Languages</p>
                  <p className="text-2xl font-bold">{knowledgeBaseStatus.languages}</p>
                </div>
              </div>
            </CardContent>
          </Card>
            
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <CheckCircle className={`w-5 h-5 ${knowledgeBaseStatus.status === 'active' ? 'text-green-500' : 'text-red-500'}`} />
                  <div>
                    <p className="text-sm font-medium">Status</p>
                    <p className="text-2xl font-bold capitalize">{knowledgeBaseStatus.status}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="space-y-6">
          {/* Upload Area */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="w-5 h-5" />
                Upload Documents
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                  isDragOver
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:border-primary/50'
                }`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                <Upload className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                <p className="text-lg font-medium mb-2">
                  Drag and drop PDF files here, or click to browse
                </p>
                <p className="text-muted-foreground mb-4">
                  Supports PDF files up to 50MB
                </p>
                <input
                  type="file"
                  multiple
                  accept=".pdf"
                  onChange={handleFileSelect}
                  className="hidden"
                  id="file-upload"
                />
                <Button asChild>
                  <label htmlFor="file-upload" className="cursor-pointer">
                    <Plus className="w-4 h-4 mr-2" />
                    Select Files
                  </label>
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Upload Tasks */}
          <AnimatePresence>
            {uploadTasks.map((task) => (
              <motion.div
                key={task.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
              >
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {getStatusIcon(task.status)}
                        <div>
                          <p className="font-medium">{task.filename}</p>
                          <p className="text-sm text-muted-foreground">
                            {task.status === 'uploading' && 'Uploading...'}
                            {task.status === 'processing' && 'Processing document...'}
                            {task.status === 'completed' && 'Processing completed!'}
                            {task.status === 'error' && (task.error || 'Error occurred')}
                          </p>
                        </div>
                      </div>
                      
                      {(task.status === 'uploading' || task.status === 'processing') && task.progress !== undefined && (
                        <div className="w-32">
                          <Progress value={task.progress} className="h-2" />
                          <p className="text-xs text-muted-foreground text-center mt-1">
                            {Math.round(task.progress)}%
                          </p>
                        </div>
                      )}
                      
                      {task.status === 'error' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setUploadTasks(prev => prev.filter(t => t.id !== task.id))}
                        >
                          <X className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Documents List */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="w-5 h-5" />
                Documents ({adminDocuments.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin" />
                  <span className="ml-2">Loading documents...</span>
                </div>
              ) : adminDocuments.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No documents uploaded yet.</p>
                  <p className="text-sm">Upload your first PDF to get started.</p>
                </div>
              ) : (
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {adminDocuments.map((document) => (
                    <div
                      key={document.id}
                      className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent/50 transition-colors"
                    >
                      <div className="flex items-center gap-4 flex-1 min-w-0">
                        <FileText className="w-8 h-8 text-blue-500 flex-shrink-0" />
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <p className="font-medium truncate">{document.original_filename}</p>
                            {getStatusBadge(document.processing_status)}
                          </div>
                          <div className="flex items-center gap-4 text-sm text-muted-foreground">
                            <span className="flex items-center gap-1">
                              <Calendar className="w-3 h-3" />
                              {formatDate(document.created_at)}
                            </span>
                            {document.file_size && (
                              <span>{formatFileSize(document.file_size)}</span>
                            )}
                            <span className="flex items-center gap-1">
                              <Languages className="w-3 h-3" />
                              {document.language}
                            </span>
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteDocument(document.id, document.original_filename)}
                        >
                          <Trash2 className="w-4 h-4 text-red-500" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};