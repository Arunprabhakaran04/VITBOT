import { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Settings, 
  Users, 
  FileText, 
  Database, 
  BarChart3, 
  Shield,
  LogOut,
  Menu,
  X
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useStore } from '@/lib/store';
import { AdminDocumentManager } from './AdminDocumentManager';
import { authAPI } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

type AdminView = 'documents' | 'users' | 'analytics' | 'settings';

export const AdminDashboard = () => {
  const { user, logout, setSidebarOpen } = useStore();
  const { toast } = useToast();
  const [currentView, setCurrentView] = useState<AdminView>('documents');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const handleLogout = async () => {
    try {
      await authAPI.logout();
      logout();
      toast({
        title: "Logged out successfully",
        description: "You have been logged out of the admin panel.",
      });
    } catch (error) {
      console.error('Logout error:', error);
      // Force logout even if API call fails
      logout();
    }
  };

  const sidebarItems = [
    {
      id: 'documents' as AdminView,
      label: 'Document Management',
      icon: FileText,
      description: 'Manage PDF documents and knowledge base'
    },
    {
      id: 'users' as AdminView,
      label: 'User Management',
      icon: Users,
      description: 'View and manage system users'
    },
    {
      id: 'analytics' as AdminView,
      label: 'Analytics',
      icon: BarChart3,
      description: 'Usage statistics and insights'
    },
    {
      id: 'settings' as AdminView,
      label: 'System Settings',
      icon: Settings,
      description: 'Configure system settings'
    }
  ];

  const renderCurrentView = () => {
    switch (currentView) {
      case 'documents':
        return <AdminDocumentManager />;
      case 'users':
        return <UserManagementPlaceholder />;
      case 'analytics':
        return <AnalyticsPlaceholder />;
      case 'settings':
        return <SettingsPlaceholder />;
      default:
        return <AdminDocumentManager />;
    }
  };

  return (
    <div className="min-h-screen bg-background flex">
      {/* Sidebar */}
      <motion.div
        className={`bg-card border-r border-border flex flex-col transition-all duration-300 ${
          sidebarCollapsed ? 'w-16' : 'w-64'
        }`}
        animate={{ width: sidebarCollapsed ? 64 : 256 }}
      >
        {/* Header */}
        <div className="p-4 border-b border-border">
          <div className="flex items-center justify-between">
            {!sidebarCollapsed && (
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
                  <Shield className="w-5 h-5 text-primary-foreground" />
                </div>
                <div>
                  <h1 className="font-bold text-foreground">Admin Panel</h1>
                  <p className="text-xs text-muted-foreground">VITBOT Management</p>
                </div>
              </div>
            )}
            
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            >
              {sidebarCollapsed ? <Menu className="w-4 h-4" /> : <X className="w-4 h-4" />}
            </Button>
          </div>
        </div>

        {/* Navigation */}
        <div className="flex-1 p-2">
          <nav className="space-y-1">
            {sidebarItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentView === item.id;
              
              return (
                <Button
                  key={item.id}
                  variant={isActive ? "secondary" : "ghost"}
                  className={`w-full justify-start gap-3 h-auto p-3 ${
                    sidebarCollapsed ? 'px-3' : ''
                  }`}
                  onClick={() => setCurrentView(item.id)}
                >
                  <Icon className="w-5 h-5 flex-shrink-0" />
                  {!sidebarCollapsed && (
                    <div className="text-left">
                      <div className="font-medium">{item.label}</div>
                      <div className="text-xs text-muted-foreground">
                        {item.description}
                      </div>
                    </div>
                  )}
                </Button>
              );
            })}
          </nav>
        </div>

        {/* User Info & Logout */}
        <div className="p-4 border-t border-border">
          {!sidebarCollapsed && (
            <div className="mb-3">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                  <Shield className="w-4 h-4 text-primary-foreground" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">
                    {user?.email}
                  </p>
                  <p className="text-xs text-muted-foreground">Administrator</p>
                </div>
              </div>
            </div>
          )}
          
          <Button
            variant="outline"
            className="w-full gap-2"
            onClick={handleLogout}
          >
            <LogOut className="w-4 h-4" />
            {!sidebarCollapsed && 'Logout'}
          </Button>
        </div>
      </motion.div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        {renderCurrentView()}
      </div>
    </div>
  );
};

// Placeholder components for other admin views
const UserManagementPlaceholder = () => (
  <div className="p-6">
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Users className="w-5 h-5" />
          User Management
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-muted-foreground">
          User management interface will be implemented here. This will include:
        </p>
        <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
          <li>• View all registered users</li>
          <li>• Manage user roles and permissions</li>
          <li>• User activity monitoring</li>
          <li>• User access controls</li>
        </ul>
      </CardContent>
    </Card>
  </div>
);

const AnalyticsPlaceholder = () => (
  <div className="p-6">
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5" />
          Analytics & Insights
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-muted-foreground">
          Analytics dashboard will be implemented here. This will include:
        </p>
        <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
          <li>• User engagement metrics</li>
          <li>• Document usage statistics</li>
          <li>• Query patterns and insights</li>
          <li>• System performance metrics</li>
          <li>• Knowledge base effectiveness</li>
        </ul>
      </CardContent>
    </Card>
  </div>
);

const SettingsPlaceholder = () => (
  <div className="p-6">
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Settings className="w-5 h-5" />
          System Settings
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-muted-foreground">
          System configuration interface will be implemented here. This will include:
        </p>
        <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
          <li>• AI model configuration</li>
          <li>• System performance tuning</li>
          <li>• Security settings</li>
          <li>• Backup and maintenance</li>
          <li>• API rate limiting</li>
        </ul>
      </CardContent>
    </Card>
  </div>
);