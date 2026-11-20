import React, { useRef, useEffect } from 'react';
import { Plus, ArrowUp, Loader2, Sparkles, Mic, Paperclip } from 'lucide-react';

interface ChatInputProps {
  input: string;
  setInput: (value: string) => void;
  onSend: () => void;
  isLoading: boolean;
  onOpenDocuments: () => void;
  placeholder?: string;
  isInitial?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  input,
  setInput,
  onSend,
  isLoading,
  onOpenDocuments,
  placeholder = "Ask TitanOps anything about your infrastructure...",
  isInitial = false
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const scrollHeight = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = `${Math.min(scrollHeight, 180)}px`;
    }
  }, [input]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isLoading && input.trim()) {
        onSend();
      }
    }
  };

  return (
    <div className={`w-full flex justify-center transition-all duration-300 ${isInitial ? 'px-4' : 'px-4'}`}>
      <div className="w-[82%] max-w-[1050px] min-h-[66px] bg-[#1E1E1E] rounded-[40px] px-5 py-2.5 flex items-center shadow-2xl border border-transparent focus-within:border-[#333333] transition-all">
        {/* Plus / Attachment Button */}
        <button
          onClick={onOpenDocuments}
          type="button"
          title="Attach or Manage SRE Runbook Documents"
          className="w-9 h-9 rounded-full hover:bg-[#2A2A2A] text-[#A3A3A3] hover:text-white flex items-center justify-center shrink-0 transition-colors mr-2"
        >
          <Plus size={20} />
        </button>

        {/* Text Input */}
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          placeholder={placeholder}
          disabled={isLoading}
          className="flex-1 bg-transparent text-[#F5F5F5] placeholder-[#737373] text-[15.5px] leading-relaxed resize-none outline-none max-h-[180px] py-1 px-1 font-sans"
        />

        {/* Right side controls matching reference */}
        <div className="flex items-center space-x-2 shrink-0 ml-2">
          {/* Think badge from ChatGPT reference screenshot */}
          <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-[#262626]/70 text-[#A3A3A3] text-xs font-medium cursor-default">
            <Sparkles size={13} className="text-blue-400" />
            <span>SRE RAG</span>
          </div>

          {/* Send / Waveform Action Button */}
          <button
            onClick={onSend}
            disabled={isLoading || !input.trim()}
            title="Send (Enter)"
            className={`w-11 h-11 rounded-full flex items-center justify-center transition-all ${
              input.trim() && !isLoading
                ? 'bg-[#3B82F6] hover:bg-blue-600 text-white cursor-pointer shadow-md shadow-blue-500/20'
                : 'bg-[#2A2A2A] text-[#737373] cursor-not-allowed'
            }`}
          >
            {isLoading ? (
              <Loader2 size={19} className="animate-spin text-white" />
            ) : (
              <ArrowUp size={20} strokeWidth={2.5} />
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
