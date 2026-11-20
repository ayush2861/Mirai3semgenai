import React from 'react';
import {
  SquarePen,
  FileText,
  BookOpen,
  AlertTriangle,
  Database,
  Search,
  PanelLeft,
  Settings as SettingsIcon,
  Trash2,
  CheckCircle2,
  ShieldAlert
} from 'lucide-react';
import { ConversationSummary } from '../types';

interface SidebarProps {
  conversations: ConversationSummary[];
  activeConvId: string | null;
  onSelectConversation: (id: string) => void;
  onNewChat: () => void;
  onDeleteConversation: (id: string, e: React.MouseEvent) => void;
  onOpenDocuments: () => void;
  onOpenRunbooks: () => void;
  onOpenIncidents: () => void;
  onOpenKnowledgeBase: () => void;
  onOpenSettings: () => void;
  onOpenSearch: () => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  activeNavView: string;
}

export const Sidebar: React.FC<SidebarProps> = ({
  conversations,
  activeConvId,
  onSelectConversation,
  onNewChat,
  onDeleteConversation,
  onOpenDocuments,
  onOpenRunbooks,
  onOpenIncidents,
  onOpenKnowledgeBase,
  onOpenSettings,
  onOpenSearch,
  isCollapsed,
  onToggleCollapse,
  activeNavView
}) => {
  if (isCollapsed) {
    return (
      <div className="w-16 h-screen bg-black border-r border-[#262626] flex flex-col items-center py-4 justify-between select-none">
        <div className="flex flex-col items-center space-y-4">
          <button
            onClick={onToggleCollapse}
            title="Expand Sidebar"
            className="p-2 text-[#A3A3A3] hover:text-white hover:bg-[#1C1C1C] rounded-lg transition-colors"
          >
            <PanelLeft size={20} />
          </button>
          <button
            onClick={onNewChat}
            title="New Chat"
            className="p-2 text-[#A3A3A3] hover:text-white hover:bg-[#1C1C1C] rounded-lg transition-colors"
          >
            <SquarePen size={20} />
          </button>
          <button
            onClick={onOpenDocuments}
            title="Documents"
            className="p-2 text-[#A3A3A3] hover:text-white hover:bg-[#1C1C1C] rounded-lg transition-colors"
          >
            <FileText size={20} />
          </button>
          <button
            onClick={onOpenRunbooks}
            title="Runbooks"
            className="p-2 text-[#A3A3A3] hover:text-white hover:bg-[#1C1C1C] rounded-lg transition-colors"
          >
            <BookOpen size={20} />
          </button>
        </div>

        <button
          onClick={onOpenSettings}
          title="Settings"
          className="p-2 text-[#A3A3A3] hover:text-white hover:bg-[#1C1C1C] rounded-lg transition-colors"
        >
          <SettingsIcon size={20} />
        </button>
      </div>
    );
  }

  return (
    <aside className="w-[388px] h-screen bg-black border-r border-[#262626] flex flex-col justify-between select-none shrink-0 font-sans">
      {/* Top Section */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Header */}
        <div className="h-14 px-4 flex items-center justify-between border-b border-transparent">
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-white text-[19px] tracking-tight">TitanOps AI</span>
            <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">SRE</span>
          </div>
          <div className="flex items-center space-x-1">
            <button
              onClick={onOpenSearch}
              title="Search (⌘K)"
              className="p-2 text-[#A3A3A3] hover:text-white hover:bg-[#141414] rounded-lg transition-colors"
            >
              <Search size={18} />
            </button>
            <button
              onClick={onToggleCollapse}
              title="Collapse Sidebar"
              className="p-2 text-[#A3A3A3] hover:text-white hover:bg-[#141414] rounded-lg transition-colors"
            >
              <PanelLeft size={18} />
            </button>
          </div>
        </div>

        {/* Primary Navigation */}
        <div className="px-3 pt-1 space-y-1">
          {/* New Chat Item */}
          <button
            onClick={onNewChat}
            className={`w-full flex items-center justify-between px-3 h-[46px] rounded-xl text-[14px] font-medium transition-all ${
              activeConvId === null && activeNavView === 'chat'
                ? 'bg-[#1C1C1C] text-white'
                : 'bg-[#141414] text-white hover:bg-[#1C1C1C]'
            }`}
          >
            <div className="flex items-center space-x-3">
              <SquarePen size={18} className="text-[#A3A3A3]" />
              <span>New chat</span>
            </div>
            <span className="text-xs text-[#737373] font-mono">⌘N</span>
          </button>

          {/* Documents */}
          <button
            onClick={onOpenDocuments}
            className={`w-full flex items-center px-3 h-[46px] rounded-xl text-[14px] font-medium transition-all ${
              activeNavView === 'documents'
                ? 'bg-[#1C1C1C] text-white'
                : 'text-[#F5F5F5] hover:bg-[#141414]'
            }`}
          >
            <div className="flex items-center space-x-3">
              <FileText size={18} className="text-[#A3A3A3]" />
              <span>Documents</span>
            </div>
          </button>

          {/* Runbooks */}
          <button
            onClick={onOpenRunbooks}
            className={`w-full flex items-center px-3 h-[46px] rounded-xl text-[14px] font-medium transition-all ${
              activeNavView === 'runbooks'
                ? 'bg-[#1C1C1C] text-white'
                : 'text-[#F5F5F5] hover:bg-[#141414]'
            }`}
          >
            <div className="flex items-center space-x-3">
              <BookOpen size={18} className="text-[#A3A3A3]" />
              <span>Runbooks</span>
            </div>
          </button>

          {/* Incident History */}
          <button
            onClick={onOpenIncidents}
            className={`w-full flex items-center px-3 h-[46px] rounded-xl text-[14px] font-medium transition-all ${
              activeNavView === 'incidents'
                ? 'bg-[#1C1C1C] text-white'
                : 'text-[#F5F5F5] hover:bg-[#141414]'
            }`}
          >
            <div className="flex items-center space-x-3">
              <AlertTriangle size={18} className="text-[#A3A3A3]" />
              <span>Incident History</span>
            </div>
          </button>

          {/* Knowledge Base */}
          <button
            onClick={onOpenKnowledgeBase}
            className={`w-full flex items-center px-3 h-[46px] rounded-xl text-[14px] font-medium transition-all ${
              activeNavView === 'knowledge'
                ? 'bg-[#1C1C1C] text-white'
                : 'text-[#F5F5F5] hover:bg-[#141414]'
            }`}
          >
            <div className="flex items-center space-x-3">
              <Database size={18} className="text-[#A3A3A3]" />
              <span>Knowledge Base</span>
            </div>
          </button>
        </div>

        {/* WORKSPACES Section */}
        <div className="px-3 pt-5 pb-2 flex-1 overflow-y-auto">
          <div className="px-3 pb-2 text-[11px] font-semibold tracking-wider text-[#737373] uppercase">
            Workspaces
          </div>

          <div className="space-y-0.5">
            {conversations.map((conv) => {
              const isActive = activeConvId === conv.id;
              return (
                <div
                  key={conv.id}
                  onClick={() => onSelectConversation(conv.id)}
                  className={`group relative flex items-center justify-between px-3 py-2.5 rounded-lg cursor-pointer text-[13.5px] transition-colors ${
                    isActive
                      ? 'bg-[#1C1C1C] text-white font-medium'
                      : 'text-[#D4D4D4] hover:bg-[#141414] hover:text-white'
                  }`}
                >
                  <span className="truncate pr-4 flex-1">{conv.title}</span>
                  <button
                    onClick={(e) => onDeleteConversation(conv.id, e)}
                    title="Delete conversation"
                    className="opacity-0 group-hover:opacity-100 p-1 text-[#737373] hover:text-[#EF4444] transition-opacity"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Bottom User Profile Section */}
      <div className="p-3 border-t border-[#262626] bg-black">
        <div
          onClick={onOpenSettings}
          className="flex items-center justify-between p-2 rounded-xl hover:bg-[#141414] cursor-pointer transition-colors"
        >
          <div className="flex items-center space-x-3">
            {/* Emerald circular avatar AU matching the reference screenshot */}
            <div className="w-9 h-9 rounded-full bg-[#059669] flex items-center justify-center text-white text-xs font-semibold tracking-wider shadow-sm">
              AU
            </div>
            <div className="flex flex-col text-left">
              <span className="text-[13.5px] font-medium text-[#F5F5F5] leading-snug">Admin User</span>
              <span className="text-[11.5px] text-[#A3A3A3] leading-none">SRE Engineer</span>
            </div>
          </div>
          <button
            title="Settings"
            className="p-1.5 text-[#A3A3A3] hover:text-white transition-colors"
          >
            <SettingsIcon size={17} />
          </button>
        </div>
      </div>
    </aside>
  );
};
