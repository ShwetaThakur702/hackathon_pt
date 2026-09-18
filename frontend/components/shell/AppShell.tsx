"use client";

import { AssistantProvider } from "@/lib/assistant-context";
import { CustomerProvider } from "@/lib/customer-context";
import AssistantLauncher from "./AssistantLauncher";
import BottomNav from "./BottomNav";
import MobileTopBar from "./MobileTopBar";
import TopNav from "./TopNav";

export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <CustomerProvider>
      <AssistantProvider>
        <TopNav />
        <MobileTopBar />
        <main className="pb-bottom-nav min-h-[calc(100vh-56px)]">{children}</main>
        <BottomNav />
        <AssistantLauncher />
      </AssistantProvider>
    </CustomerProvider>
  );
}
