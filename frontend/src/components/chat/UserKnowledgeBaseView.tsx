import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  FileText, 
  Calendar, 
  Download,
  Search,
  Info,
  BookOpen
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useStore } from '@/lib/store';
import { enhancedChatAPI } from '@/lib/api';
import type { AdminDocument } from '@/lib/store';
import { useToast } from '@/hooks/use-toast';

export const UserKnowledgeBaseView = () => {
  const [documents, setDocuments] = useState<AdminDocument[]>([]);
  const [filteredDocuments, setFilteredDocuments] = useState<AdminDocument[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  
  const { toast } = useToast();

  // Fetch available documents
  useEffect(() => {
    const fetchDocuments = async () => {
      try {
        setIsLoading(true);
        const response = await enhancedChatAPI.getKnowledgeBaseDocuments();
        const docs = response.documents || [];
        
        // Only show processed/completed documents to users
        const processedDocs = docs.filter(doc => 
          doc.processing_status === 'completed'
        );
        setDocuments(processedDocs);
        setFilteredDocuments(processedDocs);
      } catch (error) {
        console.error('Error fetching documents:', error);
        toast({
          title: "Error loading documents",
          description: "Unable to load available documents.",
          variant: "destructive",
        });
      } finally {
        setIsLoading(false);
      }
    };

    fetchDocuments();
  }, [toast]);

  // Filter documents based on search
  useEffect(() => {
    if (searchQuery.trim() === '') {
      setFilteredDocuments(documents);
    } else {
      const filtered = documents.filter(doc =>
        doc.original_filename.toLowerCase().includes(searchQuery.toLowerCase())
      );
      setFilteredDocuments(filtered);
    }
  }, [searchQuery, documents]);

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
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

  if (isLoading) {
    return (
      <div className="p-4">
        <div className="flex items-center justify-center h-40">
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
            <span className="text-muted-foreground">Loading knowledge base...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-border/30">
        <div className="flex items-center gap-2 mb-3">
          <BookOpen className="w-5 h-5 text-primary" />
          <h3 className="font-semibold text-foreground">Knowledge Base</h3>
        </div>
        
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
          <Input
            placeholder="Search documents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 bg-surface border-border/50"
          />
        </div>

        {/* Stats */}
        <div className="mt-3 flex items-center justify-between text-sm text-muted-foreground">
          <span>{documents.length} documents available</span>
          {searchQuery && (
            <span>{filteredDocuments.length} filtered results</span>
          )}
        </div>
      </div>

      {/* Document List */}
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-3">
          {filteredDocuments.length === 0 ? (
            <Card className="border-dashed">
              <CardContent className="flex flex-col items-center justify-center py-8">
                <BookOpen className="w-8 h-8 text-muted-foreground mb-3" />
                <p className="text-muted-foreground text-center">
                  {searchQuery 
                    ? `No documents found matching "${searchQuery}"`
                    : "No documents available in the knowledge base yet."
                  }
                </p>
                {!searchQuery && (
                  <p className="text-sm text-muted-foreground mt-2 text-center">
                    Documents uploaded by administrators will appear here.
                  </p>
                )}
              </CardContent>
            </Card>
          ) : (
            filteredDocuments.map((doc) => (
              <motion.div
                key={doc.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="group"
              >
                <Card className="hover:shadow-md transition-shadow cursor-pointer">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <FileText className="w-4 h-4 text-primary flex-shrink-0" />
                          <h4 className="font-medium text-foreground truncate">
                            {doc.original_filename}
                          </h4>
                        </div>
                        
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            {formatDate(doc.uploaded_at || doc.created_at)}
                          </span>
                          <span>{formatFileSize(doc.file_size || 0)}</span>
                        </div>

                        {doc.description && (
                          <p className="text-sm text-muted-foreground mt-2 line-clamp-2">
                            {doc.description}
                          </p>
                        )}
                      </div>

                      <div className="flex items-center gap-2 ml-4">
                        <Badge 
                          variant="secondary" 
                          className="text-xs bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
                        >
                          Available
                        </Badge>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))
          )}
        </div>
      </ScrollArea>

      {/* Info Footer */}
      <div className="p-4 border-t border-border/30">
        <div className="flex items-start gap-3 p-3 bg-muted/50 rounded-lg">
          <Info className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
          <div className="text-sm">
            <p className="text-foreground font-medium mb-1">Knowledge Base Access</p>
            <p className="text-muted-foreground text-xs leading-relaxed">
              You can ask questions about any of these documents in your chat. 
              The AI will search through them to provide accurate answers based on the uploaded content.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};