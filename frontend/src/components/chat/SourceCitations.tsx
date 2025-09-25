import { motion } from 'framer-motion';
import { FileText, ExternalLink } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';

interface Source {
  document: string;
  page: number | string;
  chunk_index?: number;
}

interface SourceCitationsProps {
  sources: Source[];
}

export const SourceCitations = ({ sources }: SourceCitationsProps) => {
  if (!sources || sources.length === 0) {
    return null;
  }

  // Group sources by document to avoid duplicates and show page ranges
  const groupedSources = sources.reduce((acc, source) => {
    const docName = source.document;
    if (!acc[docName]) {
      acc[docName] = {
        document: docName,
        pages: []
      };
    }
    if (!acc[docName].pages.includes(source.page)) {
      acc[docName].pages.push(source.page);
    }
    return acc;
  }, {} as Record<string, { document: string; pages: (number | string)[] }>);

  const formatPages = (pages: (number | string)[]) => {
    const sortedPages = pages.sort((a, b) => {
      const numA = typeof a === 'number' ? a : parseInt(String(a));
      const numB = typeof b === 'number' ? b : parseInt(String(b));
      return numA - numB;
    });

    if (sortedPages.length === 1) {
      return `page ${sortedPages[0]}`;
    } else if (sortedPages.length === 2) {
      return `pages ${sortedPages[0]} and ${sortedPages[1]}`;
    } else {
      return `pages ${sortedPages.slice(0, -1).join(', ')} and ${sortedPages[sortedPages.length - 1]}`;
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.1 }}
      className="mt-3 pt-3 border-t border-border/20"
    >
      <div className="flex items-center space-x-2 mb-2">
        <FileText className="w-3 h-3 text-muted-foreground" />
        <span className="text-xs font-medium text-muted-foreground">
          Sources
        </span>
      </div>
      
      <div className="space-y-2">
        {Object.values(groupedSources).map((sourceGroup, index) => (
          <motion.div
            key={`${sourceGroup.document}-${index}`}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.2, delay: 0.1 + (index * 0.05) }}
          >
            <Card className="p-2 bg-surface/50 border-border/40 hover:bg-surface/70 transition-colors">
              <div className="flex items-start justify-between space-x-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2">
                    <Badge 
                      variant="secondary" 
                      className="text-xs bg-primary/10 text-primary border-primary/20"
                    >
                      <FileText className="w-2.5 h-2.5 mr-1" />
                      PDF
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {formatPages(sourceGroup.pages)}
                    </span>
                  </div>
                  <p className="text-sm font-medium text-foreground mt-1 truncate" title={sourceGroup.document}>
                    {sourceGroup.document}
                  </p>
                </div>
                <ExternalLink className="w-3 h-3 text-muted-foreground flex-shrink-0 mt-1" />
              </div>
            </Card>
          </motion.div>
        ))}
      </div>
      
      {sources.length > Object.keys(groupedSources).length && (
        <p className="text-xs text-muted-foreground mt-2 italic">
          Multiple references found across {sources.length} sections
        </p>
      )}
    </motion.div>
  );
};