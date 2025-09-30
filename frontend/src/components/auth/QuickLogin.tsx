import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Shield, User } from 'lucide-react';

interface QuickLoginProps {
  onFillCredentials: (email: string, password: string) => void;
}

export const QuickLogin = ({ onFillCredentials }: QuickLoginProps) => {
  return (
    <div className="mt-6">
      <div className="text-center text-sm text-muted-foreground mb-3">
        Quick Login for Testing:
      </div>
      <div className="grid grid-cols-1 gap-3">
        <Card className="cursor-pointer hover:bg-muted/50 transition-colors" 
              onClick={() => onFillCredentials('admin@vitbot.com', 'admin123')}>
          <CardContent className="p-3">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                <Shield className="w-4 h-4 text-primary-foreground" />
              </div>
              <div className="text-left">
                <p className="font-medium text-sm">Administrator</p>
                <p className="text-xs text-muted-foreground">admin@vitbot.com</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="cursor-pointer hover:bg-muted/50 transition-colors" 
              onClick={() => onFillCredentials('user@example.com', 'password')}>
          <CardContent className="p-3">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
                <User className="w-4 h-4 text-secondary-foreground" />
              </div>
              <div className="text-left">
                <p className="font-medium text-sm">Regular User</p>
                <p className="text-xs text-muted-foreground">user@example.com</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
      
      <p className="text-xs text-muted-foreground mt-3 text-center">
        Click on a role to auto-fill login credentials for testing
      </p>
    </div>
  );
};