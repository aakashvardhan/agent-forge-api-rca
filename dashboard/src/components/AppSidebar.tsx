import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bot,
  Settings,
  Shield,
  Zap,
} from "lucide-react";
import { NavLink } from "@/components/NavLink";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarHeader,
  SidebarFooter,
  useSidebar,
} from "@/components/ui/sidebar";
import { usePolling } from "@/hooks/use-polling";
import { api } from "@/lib/api-client";

const mainNav = [
  { title: "Live Status", url: "/", icon: Activity },
  { title: "Chaos Control", url: "/chaos", icon: Zap },
  { title: "Incident Log", url: "/incidents", icon: AlertTriangle },
  { title: "Dashboard", url: "/dashboard", icon: BarChart3 },
];

const systemNav = [
  { title: "Agent Pipeline", url: "/agents", icon: Bot },
  { title: "Settings", url: "/settings", icon: Settings },
];

export function AppSidebar() {
  const { state } = useSidebar();
  const collapsed = state === "collapsed";
  const { data: agentStatus } = usePolling({ fetcher: api.getAgentStatus, interval: 5000 });
  const activeCount = agentStatus?.agents.filter((a) => a.status === "active").length ?? 0;

  return (
    <Sidebar collapsible="icon" className="border-r-0">
      <SidebarHeader className="p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Shield className="h-5 w-5" />
          </div>
          {!collapsed && (
            <div className="flex flex-col">
              <span className="text-sm font-bold text-sidebar-accent-foreground tracking-tight">
                AgentForge
              </span>
              <span className="text-[10px] font-medium text-sidebar-foreground uppercase tracking-widest">
                API RCA Engine
              </span>
            </div>
          )}
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel className="text-[10px] uppercase tracking-widest text-sidebar-foreground/50">
            Analysis
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {mainNav.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild>
                    <NavLink
                      to={item.url}
                      end
                      className="text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors"
                      activeClassName="bg-sidebar-accent text-sidebar-primary font-medium"
                    >
                      <item.icon className="h-4 w-4" />
                      {!collapsed && <span>{item.title}</span>}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel className="text-[10px] uppercase tracking-widest text-sidebar-foreground/50">
            System
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {systemNav.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild>
                    <NavLink
                      to={item.url}
                      end
                      className="text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors"
                      activeClassName="bg-sidebar-accent text-sidebar-primary font-medium"
                    >
                      <item.icon className="h-4 w-4" />
                      {!collapsed && <span>{item.title}</span>}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="p-4">
        {!collapsed && (
          <div className="flex items-center gap-2 rounded-lg bg-sidebar-accent p-3">
            <Zap className="h-4 w-4 text-sidebar-primary" />
            <div className="flex flex-col">
              <span className="text-[11px] font-semibold text-sidebar-accent-foreground">
                Multi-Agent Pipeline
              </span>
              <span className="text-[10px] text-sidebar-foreground">
                {activeCount} agent{activeCount !== 1 ? "s" : ""} {activeCount > 0 ? "active" : "idle"}
              </span>
            </div>
          </div>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}
