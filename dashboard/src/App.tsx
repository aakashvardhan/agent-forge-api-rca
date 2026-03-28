import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/AppSidebar";
import { ThemeProvider, useTheme } from "@/hooks/use-theme";
import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";

import LiveStatus from "./pages/LiveStatus";
import ChaosControl from "./pages/ChaosControl";
import IncidentLog from "./pages/IncidentLog";
import Dashboard from "./pages/Dashboard";
import Analyze from "./pages/Analyze";
import Metrics from "./pages/Metrics";
import AgentPipeline from "./pages/AgentPipeline";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  return (
    <Button variant="ghost" size="icon" onClick={toggleTheme} className="h-8 w-8">
      {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </Button>
  );
}

function AppLayout() {
  return (
    <SidebarProvider>
      <div className="min-h-screen flex w-full">
        <AppSidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <header className="sticky top-0 z-30 flex h-12 items-center justify-between border-b border-border bg-background/80 backdrop-blur-xl px-4">
            <SidebarTrigger />
            <ThemeToggle />
          </header>
          <main className="flex-1 p-4 md:p-6 overflow-auto">
            <Routes>
              <Route path="/" element={<LiveStatus />} />
              <Route path="/chaos" element={<ChaosControl />} />
              <Route path="/incidents" element={<IncidentLog />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/analyze" element={<Analyze />} />
              <Route path="/metrics" element={<Metrics />} />
              <Route path="/agents" element={<AgentPipeline />} />
              <Route path="/settings" element={<LiveStatus />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </main>
        </div>
      </div>
    </SidebarProvider>
  );
}

const App = () => (
  <ThemeProvider>
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <AppLayout />
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  </ThemeProvider>
);

export default App;
