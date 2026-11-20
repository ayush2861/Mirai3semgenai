import React, { useState, useRef, useCallback } from 'react';
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
  onOpenRunbooks: () => void;
  onOpenIncidents: () => void;
  onOpenKnowledgeBase: () => void;
  onOpenSettings: () => void;
  onOpenSearch: () => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  activeNavView: string;
  width?: number;
  onWidthChange?: (width: number) => void;
  minWidth?: number;
  maxWidth?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  conversations,
  activeConvId,
  onSelectConversation,
  onNewChat,
  onDeleteConversation,
  onOpenRunbooks,
  onOpenIncidents,
  onOpenKnowledgeBase,
  onOpenSettings,
  onOpenSearch,
  isCollapsed,
  onToggleCollapse,
  activeNavView,
  width = 388,
  onWidthChange,
  minWidth = 260,
  maxWidth = 720
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const isDraggingRef = useRef(false);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    isDraggingRef.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    const onMouseMove = (moveEvent: MouseEvent) => {
      if (!isDraggingRef.current) return;
      const clientX = moveEvent.clientX;

      if (isCollapsed) {
        if (clientX > 140) {
          onToggleCollapse();
          if (onWidthChange) {
            onWidthChange(Math.max(minWidth, Math.min(maxWidth, clientX)));
          }
        }
        return;
      }

      if (clientX < 150) {
        onToggleCollapse();
        return;
      }

      const clamped = Math.max(minWidth, Math.min(maxWidth, clientX));
      if (onWidthChange) {
        onWidthChange(clamped);
      }
    };

    const onMouseUp = () => {
      setIsDragging(false);
      isDraggingRef.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  }, [isCollapsed, minWidth, maxWidth, onToggleCollapse, onWidthChange]);

  const handleDoubleClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    if (onWidthChange) {
      onWidthChange(388);
    }
  }, [onWidthChange]);

  const renderResizeHandle = () => (
    <div
      onMouseDown={handleMouseDown}
      onDoubleClick={handleDoubleClick}
      className="absolute top-0 -right-2 w-4 h-full cursor-col-resize select-none z-40 flex items-center justify-center group"
      title="Drag to resize sidebar (double-click to reset)"
    >
      {/* Vertical bar highlight on hover or drag - native col-resize provides the small handle cursor */}
      <div
        className={`w-[4px] h-full transition-colors ${
          isDragging ? 'bg-[#525252]' : 'group-hover:bg-[#383838]'
        }`}
      />
    </div>
  );

  if (isCollapsed) {
    return (
      <div className="relative w-16 h-screen bg-black border-r border-[#262626] flex flex-col items-center py-4 justify-between select-none shrink-0 font-sans">
        <div className="flex flex-col items-center space-y-4">
          <div
            onClick={onOpenSettings}
            title="Admin User (Settings)"
            className="w-8 h-8 rounded-full bg-[#059669] flex items-center justify-center text-white text-xs font-semibold tracking-wider cursor-pointer shadow-sm hover:ring-2 hover:ring-white/20 transition-all"
          >
            AU
          </div>
          <button
            onClick={onToggleCollapse}
            title="Expand Sidebar"
            className="p-2 text-[#A3A3A3] hover:text-white hover:bg-[#1C1C1C] rounded-lg transition-colors"
          >
            <PanelLeft size={20} />
          </button>
          <button
            onClick={onNewChat}
            title={conversations.length >= 5 ? "New Chat (Limit reached 5/5 - delete a chat to continue)" : "New Chat"}
            className={`p-2 rounded-lg transition-colors relative ${
              conversations.length >= 5
                ? 'text-amber-400 hover:text-amber-300 hover:bg-[#1C1C1C]'
                : 'text-[#A3A3A3] hover:text-white hover:bg-[#1C1C1C]'
            }`}
          >
            <SquarePen size={20} />
            {conversations.length >= 5 && (
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-amber-400" />
            )}
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
        {renderResizeHandle()}
      </div>
    );
  }

  return (
    <aside
      style={{ width: `${width}px` }}
      className={`relative h-screen bg-black border-r border-[#262626] flex flex-col justify-between select-none shrink-0 font-sans ${
        isDragging ? '' : 'transition-[width] duration-150 ease-out'
      }`}
    >
      {/* Top Section */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Header with User Profile at the Top */}
        <div className="h-14 px-4 flex items-center justify-between border-b border-[#222222]">
          <div
            onClick={onOpenSettings}
            className="flex items-center space-x-3 cursor-pointer group p-1 -ml-1 rounded-xl hover:bg-[#141414] transition-colors"
          >
            {/* Emerald circular avatar AU */}
            <div className="w-8 h-8 rounded-full bg-[#059669] flex items-center justify-center text-white text-xs font-semibold tracking-wider shadow-sm">
              AU
            </div>
            <div className="flex flex-col text-left">
              <span className="text-[13.5px] font-medium text-[#F5F5F5] leading-snug group-hover:text-white">Admin User</span>
              <span className="text-[11px] text-[#A3A3A3] leading-none">SRE Engineer</span>
            </div>
          </div>
          <div className="flex items-center space-x-1">
            <button
              onClick={onOpenSettings}
              title="Settings"
              className="p-2 text-[#A3A3A3] hover:text-white hover:bg-[#141414] rounded-lg transition-colors"
            >
              <SettingsIcon size={17} />
            </button>
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
              conversations.length >= 5
                ? 'bg-[#181818] text-[#E5E5E5] border border-amber-500/30 hover:bg-[#202020]'
                : activeConvId === null && activeNavView === 'chat'
                ? 'bg-[#1C1C1C] text-white'
                : 'bg-[#141414] text-white hover:bg-[#1C1C1C]'
            }`}
          >
            <div className="flex items-center space-x-3">
              <SquarePen size={18} className={conversations.length >= 5 ? "text-amber-400" : "text-[#A3A3A3]"} />
              <span>New chat</span>
            </div>
            {conversations.length >= 5 ? (
              <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                5/5 Max
              </span>
            ) : (
              <span className="text-xs text-[#737373] font-mono">⌘N</span>
            )}
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
          <div className="px-3 pb-2 text-[11px] font-semibold tracking-wider text-[#737373] uppercase flex items-center justify-between">
            <span>Workspaces</span>
            <span className={`text-[10px] font-mono ${conversations.length >= 5 ? 'text-amber-400 font-semibold' : 'text-[#666666]'}`}>
              {conversations.length}/5
            </span>
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

      {/* Resize Handle Divider */}
      {renderResizeHandle()}
    </aside>
  );
};
