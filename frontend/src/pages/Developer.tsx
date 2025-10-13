import { motion } from "framer-motion";
import { ArrowLeft, Linkedin, Github, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useNavigate } from "react-router-dom";

const developers = [
  {
    name: "Arun P",
    id: "22BCE2572",
    linkedin: "https://www.linkedin.com/in/arun-prabhakaran04/",
    avatar: "AP",
  },
  {
    name: "Ranesh R K",
    id: "22BCE2260",
    linkedin: "https://www.linkedin.com/in/ranesh-rk-41a305260/",
    avatar: "RK",
  },
  {
    name: "Harshit P G",
    id: "22BCE0562",
    linkedin: "https://www.linkedin.com/in/harshit-p-g-a87623272/",
    avatar: "HPG",
  },
];

const Developer = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b border-border/30 bg-surface/30 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center space-x-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate(-1)}
              className="text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>

            <div>
              <h1 className="text-2xl font-bold text-foreground">
                Meet the Developers
              </h1>
              <p className="text-muted-foreground">The team behind SAGE</p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="max-w-4xl mx-auto"
        >
          {/* Introduction */}
          <div className="text-center mb-12">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="w-20 h-20 mx-auto mb-6 gradient-primary rounded-2xl flex items-center justify-center"
            >
              <Github className="w-10 h-10 text-white" />
            </motion.div>

            <h2 className="text-3xl font-bold text-foreground mb-4">
              Built with passion
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              SAGE is developed by a dedicated team of students who are
              passionate about creating innovative AI-powered solutions for
              document analysis and intelligent conversations.
            </p>
          </div>

          {/* Developer Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {developers.map((developer, index) => (
              <motion.div
                key={developer.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                <Card className="group hover:shadow-lg transition-all duration-300 border-border/50 hover:border-primary/30 bg-surface/50 backdrop-blur-sm">
                  <CardContent className="p-6 text-center">
                    {/* Avatar */}
                    <div className="relative mb-4">
                      <div className="w-20 h-20 mx-auto gradient-primary rounded-full flex items-center justify-center text-white font-bold text-xl group-hover:scale-105 transition-transform duration-300">
                        {developer.avatar}
                      </div>
                    </div>

                    {/* Name and ID */}
                    <h3 className="text-2xl font-semibold text-foreground mb-1">
                      {developer.name}
                    </h3>
                    <p className="text-lg text-muted-foreground mb-4 font-mono">
                      {developer.id}
                    </p>

                    {/* Social Links */}
                    <div className="flex justify-center space-x-3">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          window.open(developer.linkedin, "_blank")
                        }
                        className="hover:bg-blue-50 hover:border-blue-200 hover:text-blue-600 transition-all duration-200"
                      >
                        <Linkedin className="w-4 h-4 mr-1" />
                        LinkedIn
                      </Button>

                      {/* <Button
                        variant="ghost"
                        size="sm"
                        className="hover:bg-gray-50 hover:text-gray-600 transition-all duration-200"
                      >
                        <Mail className="w-4 h-4" />
                      </Button> */}
                    </div>

                    {/* Hover Effect */}
                    <div className="mt-4 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                      <div className="h-1 w-12 mx-auto bg-gradient-to-r from-primary to-secondary rounded-full"></div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>

          {/* Project Info */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="mt-12 text-center"
          >
            <Card className="bg-gradient-to-r from-primary/5 to-secondary/5 border-primary/20">
              <CardContent className="p-8">
                <h3 className="text-2xl font-bold text-foreground mb-4">
                  About SAGE
                </h3>
                <p className="text-muted-foreground mb-6 max-w-2xl mx-auto">
                  SAGE (Smart AI Generative Engine) is an intelligent document
                  analysis platform that combines the power of artificial
                  intelligence with intuitive user experience to help users
                  interact with their documents in meaningful ways.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
                  <div className="text-center">
                    <div className="w-12 h-12 mx-auto mb-3 bg-primary/10 rounded-lg flex items-center justify-center">
                      <span className="text-2xl">🤖</span>
                    </div>
                    <h4 className="font-semibold text-foreground mb-1">
                      AI-Powered
                    </h4>
                    <p className="text-sm text-muted-foreground">
                      Advanced language models for intelligent responses
                    </p>
                  </div>

                  <div className="text-center">
                    <div className="w-12 h-12 mx-auto mb-3 bg-primary/10 rounded-lg flex items-center justify-center">
                      <span className="text-2xl">📄</span>
                    </div>
                    <h4 className="font-semibold text-foreground mb-1">
                      Document Analysis
                    </h4>
                    <p className="text-sm text-muted-foreground">
                      Deep understanding of document content
                    </p>
                  </div>

                  <div className="text-center">
                    <div className="w-12 h-12 mx-auto mb-3 bg-primary/10 rounded-lg flex items-center justify-center">
                      <span className="text-2xl">💬</span>
                    </div>
                    <h4 className="font-semibold text-foreground mb-1">
                      Interactive Chat
                    </h4>
                    <p className="text-sm text-muted-foreground">
                      Natural conversations about your documents
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
};

export default Developer;
