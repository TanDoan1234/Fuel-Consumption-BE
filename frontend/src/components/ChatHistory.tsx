import { useState } from 'react';
import * as React from 'react';
import { Button } from './ui/button';
import { History, Trash2, Clock, MessageCircle, Star, Search, MessageSquare } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { Conversation } from '../utils/mockData';
import { ThemeColor } from '../App';
import { toast } from 'sonner@2.0.3';
import fluxmareLogo from 'figma:asset/48159e3c19318e6ee94d6f46a7da4911deba57ae.png';
import { getLogoFilter, getLogoOpacity, getContrastColor, getSecondaryTextColor, getIconColor } from '../utils/logoUtils';

interface ChatHistoryProps {
  conversations: Conversation[];
  activeConversationId: string | null;
  username: string;
  onSelectConversation: (conversationId: string) => void | Promise<void>;
  onNewConversation: () => void | Promise<void>;
  onClearHistory: () => void | Promise<void>;
  onToggleFavorite: (conversationId: string) => void | Promise<void>;
  onDeleteConversation: (conversationId: string) => void | Promise<void>;
  themeColor: ThemeColor;
  isDarkMode: boolean;
  customColor?: string;
  isLoading?: boolean;
}

export default function ChatHistory({ 
  conversations, 
  activeConversationId,
  username, 
  onSelectConversation,
  onNewConversation,
  onClearHistory,
  onToggleFavorite,
  onDeleteConversation,
  themeColor,
  isDarkMode,
  customColor,
  isLoading = false
}: ChatHistoryProps) {
  const [searchTerm, setSearchTerm] = useState('');

  const totalAnalyses = conversations.reduce((acc, conv) =>
    acc +
    conv.messages.filter(m =>
      m.type === 'bot' &&
      (m.isFuelPrediction ||
        Boolean(m.dashboardData) ||
        Boolean((m.metadata as Record<string, any> | undefined)?.prediction_made) ||
        Boolean((m.metadata as Record<string, any> | undefined)?.prediction_result))
    ).length
  , 0);

  const responseStats = conversations.reduce(
    (acc, conv) => {
      conv.messages.forEach((message, index) => {
        if (message.type !== 'bot') {
          return;
        }

        if (typeof message.responseTime === 'number' && !Number.isNaN(message.responseTime)) {
          acc.total += message.responseTime;
          acc.count += 1;
          return;
        }

        for (let i = index - 1; i >= 0; i -= 1) {
          const prevMessage = conv.messages[i];
          if (prevMessage.type === 'user') {
            const diff = message.timestamp.getTime() - prevMessage.timestamp.getTime();
            if (diff > 0) {
              acc.total += diff;
              acc.count += 1;
            }
            break;
          }
        }
      });
      return acc;
    },
    { total: 0, count: 0 }
  );

  const avgResponseTime = responseStats.count > 0 ? responseStats.total / responseStats.count : 0;

  const filteredConversations = conversations
    .filter(conv => 
      conv.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      conv.messages.some(m => m.content.toLowerCase().includes(searchTerm.toLowerCase()))
    )
    .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());

  const displayedConversations = filteredConversations;

  // Theme colors based on themeColor and isDarkMode
  const getColors = (theme: ThemeColor, dark: boolean) => {
    const base = {
      default: dark 
        ? { bg: 'bg-[#0a0a0a]', bgSecondary: 'bg-[#1a1a1a]', border: 'border-[#e3d5f7]/30', text: 'text-[#e5e5e5]', accent: 'text-[#e3d5f7]', primary: 'bg-[#7c3aed]', primaryHover: 'hover:bg-[#6d28d9]', primaryText: 'text-white', inputBg: 'bg-[#0a0a0a]', placeholderFocus: 'focus:border-[#e3d5f7]' }
        : { bg: 'bg-white', bgSecondary: 'bg-white/80', border: 'border-[#2002a6]/50', text: 'text-[#1a1a1a]', accent: 'text-[#2002a6]', primary: 'bg-[#2002a6]', primaryHover: 'hover:bg-[#1a0285]', primaryText: 'text-white', inputBg: 'bg-white', placeholderFocus: 'focus:border-[#2002a6]' },
      pink: dark
        ? { bg: 'bg-[#0a0a0a]', bgSecondary: 'bg-[#1a1a1a]', border: 'border-pink-400/30', text: 'text-pink-50', accent: 'text-pink-300', primary: 'bg-pink-500', primaryHover: 'hover:bg-pink-600', primaryText: 'text-white', inputBg: 'bg-black', placeholderFocus: 'focus:border-pink-400' }
        : { bg: 'bg-white', bgSecondary: 'bg-white/80', border: 'border-pink-400/50', text: 'text-pink-950', accent: 'text-pink-700', primary: 'bg-pink-600', primaryHover: 'hover:bg-pink-700', primaryText: 'text-white', inputBg: 'bg-white', placeholderFocus: 'focus:border-pink-400' },
      blue: dark
        ? { bg: 'bg-[#0a0a0a]', bgSecondary: 'bg-[#1a1a1a]', border: 'border-blue-400/50', text: 'text-blue-50', accent: 'text-blue-300', primary: 'bg-blue-500', primaryHover: 'hover:bg-blue-600', primaryText: 'text-white', inputBg: 'bg-black', placeholderFocus: 'focus:border-blue-400' }
        : { bg: 'bg-white', bgSecondary: 'bg-white/80', border: 'border-blue-400/50', text: 'text-blue-950', accent: 'text-blue-700', primary: 'bg-blue-600', primaryHover: 'hover:bg-blue-700', primaryText: 'text-white', inputBg: 'bg-white', placeholderFocus: 'focus:border-blue-400' },
      purple: dark
        ? { bg: 'bg-[#0a0a0a]', bgSecondary: 'bg-[#1a1a1a]', border: 'border-purple-400/50', text: 'text-purple-50', accent: 'text-purple-300', primary: 'bg-purple-500', primaryHover: 'hover:bg-purple-600', primaryText: 'text-white', inputBg: 'bg-black', placeholderFocus: 'focus:border-purple-400' }
        : { bg: 'bg-white', bgSecondary: 'bg-white/80', border: 'border-purple-400/50', text: 'text-purple-950', accent: 'text-purple-700', primary: 'bg-purple-600', primaryHover: 'hover:bg-purple-700', primaryText: 'text-white', inputBg: 'bg-white', placeholderFocus: 'focus:border-purple-400' },
      ocean: dark
        ? { bg: 'bg-[#0a0a0a]', bgSecondary: 'bg-[#1a1a1a]', border: 'border-cyan-400/50', text: 'text-cyan-50', accent: 'text-cyan-300', primary: 'bg-cyan-500', primaryHover: 'hover:bg-cyan-600', primaryText: 'text-white', inputBg: 'bg-black', placeholderFocus: 'focus:border-cyan-400' }
        : { bg: 'bg-white', bgSecondary: 'bg-white/80', border: 'border-cyan-400/50', text: 'text-cyan-950', accent: 'text-cyan-700', primary: 'bg-cyan-600', primaryHover: 'hover:bg-cyan-700', primaryText: 'text-white', inputBg: 'bg-white', placeholderFocus: 'focus:border-cyan-400' },
      sunset: dark
        ? { bg: 'bg-[#0a0a0a]', bgSecondary: 'bg-[#1a1a1a]', border: 'border-orange-400/50', text: 'text-orange-50', accent: 'text-orange-300', primary: 'bg-orange-500', primaryHover: 'hover:bg-orange-600', primaryText: 'text-white', inputBg: 'bg-black', placeholderFocus: 'focus:border-orange-400' }
        : { bg: 'bg-white', bgSecondary: 'bg-white/80', border: 'border-orange-400/50', text: 'text-orange-950', accent: 'text-orange-700', primary: 'bg-orange-500', primaryHover: 'hover:bg-orange-600', primaryText: 'text-white', inputBg: 'bg-white', placeholderFocus: 'focus:border-orange-400' },
      emerald: dark
        ? { bg: 'bg-[#0a0a0a]', bgSecondary: 'bg-[#1a1a1a]', border: 'border-emerald-400/50', text: 'text-emerald-50', accent: 'text-emerald-300', primary: 'bg-emerald-500', primaryHover: 'hover:bg-emerald-600', primaryText: 'text-white', inputBg: 'bg-black', placeholderFocus: 'focus:border-emerald-400' }
        : { bg: 'bg-white', bgSecondary: 'bg-white/80', border: 'border-emerald-400/50', text: 'text-emerald-950', accent: 'text-emerald-700', primary: 'bg-emerald-600', primaryHover: 'hover:bg-emerald-700', primaryText: 'text-white', inputBg: 'bg-white', placeholderFocus: 'focus:border-emerald-400' },
      rose: dark
        ? { bg: 'bg-[#0a0a0a]', bgSecondary: 'bg-[#1a1a1a]', border: 'border-rose-400/50', text: 'text-rose-50', accent: 'text-rose-300', primary: 'bg-rose-500', primaryHover: 'hover:bg-rose-600', primaryText: 'text-white', inputBg: 'bg-black', placeholderFocus: 'focus:border-rose-400' }
        : { bg: 'bg-white', bgSecondary: 'bg-white/80', border: 'border-rose-400/50', text: 'text-rose-950', accent: 'text-rose-700', primary: 'bg-rose-600', primaryHover: 'hover:bg-rose-700', primaryText: 'text-white', inputBg: 'bg-white', placeholderFocus: 'focus:border-rose-400' },
      fuchsia: dark
        ? { bg: 'bg-[#0a0a0a]', bgSecondary: 'bg-[#1a1a1a]', border: 'border-fuchsia-400/50', text: 'text-fuchsia-50', accent: 'text-fuchsia-300', primary: 'bg-fuchsia-500', primaryHover: 'hover:bg-fuchsia-600', primaryText: 'text-white', inputBg: 'bg-black', placeholderFocus: 'focus:border-fuchsia-400' }
        : { bg: 'bg-white', bgSecondary: 'bg-white/80', border: 'border-fuchsia-400/50', text: 'text-fuchsia-950', accent: 'text-fuchsia-700', primary: 'bg-fuchsia-600', primaryHover: 'hover:bg-fuchsia-700', primaryText: 'text-white', inputBg: 'bg-white', placeholderFocus: 'focus:border-fuchsia-400' },
      indigo: dark
        ? { bg: 'bg-[#0a0a0a]', bgSecondary: 'bg-[#1a1a1a]', border: 'border-indigo-400/50', text: 'text-indigo-50', accent: 'text-indigo-300', primary: 'bg-indigo-500', primaryHover: 'hover:bg-indigo-600', primaryText: 'text-white', inputBg: 'bg-black', placeholderFocus: 'focus:border-indigo-400' }
        : { bg: 'bg-white', bgSecondary: 'bg-white/80', border: 'border-indigo-400/50', text: 'text-indigo-950', accent: 'text-indigo-700', primary: 'bg-indigo-600', primaryHover: 'hover:bg-indigo-700', primaryText: 'text-white', inputBg: 'bg-white', placeholderFocus: 'focus:border-indigo-400' },
      sky: dark
        ? { bg: 'bg-[#0a0a0a]', bgSecondary: 'bg-[#1a1a1a]', border: 'border-sky-400/50', text: 'text-sky-50', accent: 'text-sky-300', primary: 'bg-sky-500', primaryHover: 'hover:bg-sky-600', primaryText: 'text-white', inputBg: 'bg-black', placeholderFocus: 'focus:border-sky-400' }
        : { bg: 'bg-white', bgSecondary: 'bg-white/80', border: 'border-sky-400/50', text: 'text-sky-950', accent: 'text-sky-700', primary: 'bg-sky-600', primaryHover: 'hover:bg-sky-700', primaryText: 'text-white', inputBg: 'bg-white', placeholderFocus: 'focus:border-sky-400' },
      teal: dark
        ? { bg: 'bg-[#0a0a0a]', bgSecondary: 'bg-[#1a1a1a]', border: 'border-teal-400/50', text: 'text-teal-50', accent: 'text-teal-300', primary: 'bg-teal-500', primaryHover: 'hover:bg-teal-600', primaryText: 'text-white', inputBg: 'bg-black', placeholderFocus: 'focus:border-teal-400' }
        : { bg: 'bg-white', bgSecondary: 'bg-white/80', border: 'border-teal-400/50', text: 'text-teal-950', accent: 'text-teal-700', primary: 'bg-teal-600', primaryHover: 'hover:bg-teal-700', primaryText: 'text-white', inputBg: 'bg-white', placeholderFocus: 'focus:border-teal-400' },
      lime: dark
        ? { bg: 'bg-[#0a0a0a]', bgSecondary: 'bg-[#1a1a1a]', border: 'border-lime-400/50', text: 'text-lime-50', accent: 'text-lime-300', primary: 'bg-lime-500', primaryHover: 'hover:bg-lime-600', primaryText: 'text-white', inputBg: 'bg-black', placeholderFocus: 'focus:border-lime-400' }
        : { bg: 'bg-white', bgSecondary: 'bg-white/80', border: 'border-lime-400/50', text: 'text-lime-950', accent: 'text-lime-700', primary: 'bg-lime-600', primaryHover: 'hover:bg-lime-700', primaryText: 'text-white', inputBg: 'bg-white', placeholderFocus: 'focus:border-lime-400' },
      amber: dark
        ? { bg: 'bg-[#0a0a0a]', bgSecondary: 'bg-[#1a1a1a]', border: 'border-amber-400/50', text: 'text-amber-50', accent: 'text-amber-300', primary: 'bg-amber-500', primaryHover: 'hover:bg-amber-600', primaryText: 'text-white', inputBg: 'bg-black', placeholderFocus: 'focus:border-amber-400' }
        : { bg: 'bg-white', bgSecondary: 'bg-white/80', border: 'border-amber-400/50', text: 'text-amber-950', accent: 'text-amber-700', primary: 'bg-amber-600', primaryHover: 'hover:bg-amber-700', primaryText: 'text-white', inputBg: 'bg-white', placeholderFocus: 'focus:border-amber-400' },
      custom: dark
        ? { bg: 'bg-[#0a0a0a]', bgSecondary: 'bg-[#1a1a1a]', border: 'border-white/50', text: 'text-white', accent: 'text-white', primary: 'bg-white', primaryHover: 'hover:bg-gray-200', primaryText: 'text-black', inputBg: 'bg-black', placeholderFocus: 'focus:border-white' }
        : { bg: 'bg-white', bgSecondary: 'bg-white/80', border: 'border-gray-900/50', text: 'text-gray-900', accent: 'text-gray-900', primary: 'bg-gray-900', primaryHover: 'hover:bg-gray-800', primaryText: 'text-white', inputBg: 'bg-white', placeholderFocus: 'focus:border-gray-900' },
    };
    return base[theme];
  };

  const colors = getColors(themeColor, isDarkMode);

  return (
    <div className={`w-72 ${colors.bg} border-r-2 ${colors.border} flex flex-col shadow-2xl h-screen overflow-hidden text-sm`}>
      {/* Header - FIXED */}
      <div className={`p-2 border-b-2 ${colors.border} ${colors.bgSecondary} flex-shrink-0`}>
        <motion.div 
          className={`flex items-center justify-between ${colors.text} mb-2`}
          initial={{ x: -20, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
        >
          <div className="flex items-center gap-2">
            <img 
              src={fluxmareLogo} 
              alt="Fluxmare Logo" 
              className="h-7 w-7 object-contain"
              style={{
                filter: getLogoFilter(isDarkMode, themeColor),
                opacity: getLogoOpacity()
              }}
            />
            <div>
              <h2 
                className="text-sm"
                style={{ color: getContrastColor(isDarkMode, themeColor, customColor) }}
              >
                Fluxmare
              </h2>
              <p 
                className="text-xs" 
                style={{ color: getSecondaryTextColor(isDarkMode, themeColor, customColor) }}
              >
                Lịch sử phân tích
              </p>
            </div>
          </div>
          <Button
            onClick={onNewConversation}
            size="sm"
            className={`${colors.primary} ${colors.primaryHover} ${colors.primaryText} text-xs h-7 px-2 shadow-lg`}
          >
            <MessageSquare className="h-3 w-3 mr-1" />
            Mới
          </Button>
        </motion.div>
        <div 
          className="text-xs" 
          style={{ color: getSecondaryTextColor(isDarkMode, themeColor, customColor) }}
        >
          <p>
            Người dùng: <span style={{ color: getContrastColor(isDarkMode, themeColor, customColor) }}>{username}</span>
          </p>
        </div>
      </div>

      {/* Stats - FIXED */}
      <div className={`p-2 ${colors.bgSecondary} border-b-2 ${colors.border} flex-shrink-0`}>
        <div className="grid grid-cols-2 gap-2">
          <motion.div 
            className={`${colors.bgSecondary} rounded-lg p-2 border-2 ${colors.border} backdrop-blur-sm`}
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.1 }}
          >
            <div 
              className="flex items-center gap-1 mb-1"
              style={{ color: getSecondaryTextColor(isDarkMode, themeColor, customColor) }}
            >
              <MessageCircle className="h-3 w-3" />
              <span className="text-xs">Phân tích</span>
            </div>
            <div 
              className="text-lg"
              style={{ color: getContrastColor(isDarkMode, themeColor, customColor) }}
            >
              {totalAnalyses}
            </div>
          </motion.div>
          <motion.div 
            className={`${colors.bgSecondary} rounded-lg p-2 border-2 ${colors.border} backdrop-blur-sm`}
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            <div 
              className="flex items-center gap-1 mb-1"
              style={{ color: getSecondaryTextColor(isDarkMode, themeColor, customColor) }}
            >
              <Clock className="h-3 w-3" />
              <span className="text-xs">Phản hồi</span>
            </div>
            <div 
              className="text-lg"
              style={{ color: getContrastColor(isDarkMode, themeColor, customColor) }}
            >
              {avgResponseTime.toFixed(0)}ms
            </div>
          </motion.div>
        </div>
      </div>

      {/* Search Bar - FIXED */}
      <div className={`p-2 border-b-2 ${colors.border} ${colors.bgSecondary} flex-shrink-0`}>
        <div className="relative">
          <Search 
            className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3" 
            style={{ color: getIconColor(isDarkMode, themeColor, customColor) }}
          />
          <input
            type="text"
            placeholder="Tìm kiếm lịch sử..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className={`w-full pl-8 pr-2 py-1.5 text-xs rounded-lg border-2 ${colors.border} ${colors.inputBg} focus:outline-none ${colors.placeholderFocus}`}
            style={{ color: getContrastColor(isDarkMode, themeColor, customColor) }}
          />
        </div>
      </div>

      {/* Scrollable conversations */}
      <div className={`flex-1 min-h-0 overflow-y-auto p-2 ${colors.bg}`}>
        <div className="space-y-2">
          {isLoading ? (
            <div
              className="text-center py-8 text-xs"
              style={{ color: getSecondaryTextColor(isDarkMode, themeColor, customColor) }}
            >
              Dang tai cuoc tro chuyen...
            </div>
          ) : filteredConversations.length === 0 ? (
            <motion.div 
              className="text-center py-8"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              style={{ color: getSecondaryTextColor(isDarkMode, themeColor, customColor) }}
            >
              <History 
                className="h-12 w-12 mx-auto mb-2 opacity-50" 
                style={{ color: getIconColor(isDarkMode, themeColor, customColor) }}
              />
              <p className="text-sm">
                {searchTerm ? 'Không tìm thấy kết quả' : 'Chưa có lịch sử'}
              </p>
            </motion.div>
          ) : (
            <>
              <div>
                <h3 
                  className="text-xs mb-2 flex items-center gap-1"
                  style={{ color: getContrastColor(isDarkMode, themeColor, customColor, 0.9) }}
                >
                  <MessageCircle 
                    className="h-3 w-3" 
                    style={{ color: getIconColor(isDarkMode, themeColor, customColor) }}
                  />
                  Cuộc trò chuyện
                </h3>
                {displayedConversations.map((conv, idx) => (
                  <ConversationItem
                    key={conv.id}
                    conversation={conv}
                    isActive={conv.id === activeConversationId}
                    themeColor={themeColor}
                    isDarkMode={isDarkMode}
                    index={idx}
                    customColor={customColor}
                    onSelect={() => onSelectConversation(conv.id)}
                    onToggleFavorite={() => onToggleFavorite(conv.id)}
                    onDelete={() => onDeleteConversation(conv.id)}
                  />
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Action Buttons - FIXED AT BOTTOM */}
      <div className={`p-2 border-t-2 ${colors.border} ${colors.bgSecondary} flex-shrink-0 space-y-2`}>
        {/* Compare Dialog */}

        
        {/* Clear History */}
        {conversations.length > 0 && (
          <Button
            onClick={onClearHistory}
            variant="outline"
            size="sm"
            className="w-full border-2 border-red-500 text-red-500 hover:bg-red-500 hover:text-white text-xs h-8"
          >
            <Trash2 className="h-3 w-3 mr-1" />
            Xóa lịch sử
          </Button>
        )}
      </div>
    </div>
  );
}

interface ConversationItemProps {
  conversation: Conversation;
  isActive: boolean;
  themeColor: ThemeColor;
  isDarkMode?: boolean;
  index: number;
  onSelect: () => void;
  onToggleFavorite: () => void;
  onDelete: () => void;
  customColor?: string;
}

function ConversationItem({ conversation, isActive, themeColor, isDarkMode = true, index, onSelect, onToggleFavorite, onDelete, customColor }: ConversationItemProps) {
  const messageCount =
    conversation.messageCount ??
    conversation.messages.length;
  const formattedTime = formatConversationTimestamp(conversation.timestamp);
  const [showDeleteConfirm, setShowDeleteConfirm] = React.useState(false);

  const getColors = (theme: ThemeColor, dark: boolean) => {
    const base = {
      default: dark
        ? { bg: 'bg-[#1a1a1a]/50', activeBg: 'bg-[#e3d5f7]/10', border: 'border-[#e3d5f7]/30', activeBorder: 'border-[#e3d5f7]', text: 'text-[#e5e5e5]', accent: 'text-[#e3d5f7]', hover: 'hover:border-[#e3d5f7]', secondary: 'text-[#a0a0a0]' }
        : { bg: 'bg-white/50', activeBg: 'bg-[#2002a6]/10', border: 'border-[#2002a6]/50', activeBorder: 'border-[#2002a6]', text: 'text-[#1a1a1a]', accent: 'text-[#2002a6]', hover: 'hover:border-[#2002a6]', secondary: 'text-[#525252]' },
      pink: dark
        ? { bg: 'bg-[#1a1a1a]/50', activeBg: 'bg-pink-500/10', border: 'border-pink-400/30', activeBorder: 'border-pink-400', text: 'text-pink-50', accent: 'text-pink-300', hover: 'hover:border-pink-400', secondary: 'text-pink-200' }
        : { bg: 'bg-white/50', activeBg: 'bg-pink-500/10', border: 'border-pink-400/30', activeBorder: 'border-pink-600', text: 'text-pink-950', accent: 'text-pink-700', hover: 'hover:border-pink-600', secondary: 'text-pink-800' },
      blue: dark
        ? { bg: 'bg-[#1a1a1a]/50', activeBg: 'bg-blue-500/10', border: 'border-blue-400/30', activeBorder: 'border-blue-400', text: 'text-blue-50', accent: 'text-blue-300', hover: 'hover:border-blue-400', secondary: 'text-blue-200' }
        : { bg: 'bg-white/50', activeBg: 'bg-blue-500/10', border: 'border-blue-400/30', activeBorder: 'border-blue-600', text: 'text-blue-950', accent: 'text-blue-700', hover: 'hover:border-blue-600', secondary: 'text-blue-800' },
      purple: dark
        ? { bg: 'bg-[#1a1a1a]/50', activeBg: 'bg-purple-500/10', border: 'border-purple-400/30', activeBorder: 'border-purple-400', text: 'text-purple-50', accent: 'text-purple-300', hover: 'hover:border-purple-400', secondary: 'text-purple-200' }
        : { bg: 'bg-white/50', activeBg: 'bg-purple-500/10', border: 'border-purple-400/30', activeBorder: 'border-purple-600', text: 'text-purple-950', accent: 'text-purple-700', hover: 'hover:border-purple-600', secondary: 'text-purple-800' },
      ocean: dark
        ? { bg: 'bg-[#1a1a1a]/50', activeBg: 'bg-cyan-500/10', border: 'border-cyan-400/30', activeBorder: 'border-cyan-400', text: 'text-cyan-50', accent: 'text-cyan-300', hover: 'hover:border-cyan-400', secondary: 'text-cyan-200' }
        : { bg: 'bg-white/50', activeBg: 'bg-cyan-500/10', border: 'border-cyan-400/30', activeBorder: 'border-cyan-600', text: 'text-cyan-950', accent: 'text-cyan-700', hover: 'hover:border-cyan-600', secondary: 'text-cyan-800' },
      sunset: dark
        ? { bg: 'bg-[#1a1a1a]/50', activeBg: 'bg-orange-500/10', border: 'border-orange-400/30', activeBorder: 'border-orange-400', text: 'text-orange-50', accent: 'text-orange-300', hover: 'hover:border-orange-400', secondary: 'text-orange-200' }
        : { bg: 'bg-white/50', activeBg: 'bg-orange-500/10', border: 'border-orange-400/30', activeBorder: 'border-orange-600', text: 'text-orange-950', accent: 'text-orange-700', hover: 'hover:border-orange-600', secondary: 'text-orange-800' },
      emerald: dark
        ? { bg: 'bg-[#1a1a1a]/50', activeBg: 'bg-emerald-500/10', border: 'border-emerald-400/30', activeBorder: 'border-emerald-400', text: 'text-emerald-50', accent: 'text-emerald-300', hover: 'hover:border-emerald-400', secondary: 'text-emerald-200' }
        : { bg: 'bg-white/50', activeBg: 'bg-emerald-500/10', border: 'border-emerald-400/30', activeBorder: 'border-emerald-600', text: 'text-emerald-950', accent: 'text-emerald-700', hover: 'hover:border-emerald-600', secondary: 'text-emerald-800' },
      rose: dark
        ? { bg: 'bg-[#1a1a1a]/50', activeBg: 'bg-rose-500/10', border: 'border-rose-400/30', activeBorder: 'border-rose-400', text: 'text-rose-50', accent: 'text-rose-300', hover: 'hover:border-rose-400', secondary: 'text-rose-200' }
        : { bg: 'bg-white/50', activeBg: 'bg-rose-500/10', border: 'border-rose-400/30', activeBorder: 'border-rose-600', text: 'text-rose-950', accent: 'text-rose-700', hover: 'hover:border-rose-600', secondary: 'text-rose-800' },
      fuchsia: dark
        ? { bg: 'bg-[#1a1a1a]/50', activeBg: 'bg-fuchsia-500/10', border: 'border-fuchsia-400/30', activeBorder: 'border-fuchsia-400', text: 'text-fuchsia-50', accent: 'text-fuchsia-300', hover: 'hover:border-fuchsia-400', secondary: 'text-fuchsia-200' }
        : { bg: 'bg-white/50', activeBg: 'bg-fuchsia-500/10', border: 'border-fuchsia-400/30', activeBorder: 'border-fuchsia-600', text: 'text-fuchsia-950', accent: 'text-fuchsia-700', hover: 'hover:border-fuchsia-600', secondary: 'text-fuchsia-800' },
      indigo: dark
        ? { bg: 'bg-[#1a1a1a]/50', activeBg: 'bg-indigo-500/10', border: 'border-indigo-400/30', activeBorder: 'border-indigo-400', text: 'text-indigo-50', accent: 'text-indigo-300', hover: 'hover:border-indigo-400', secondary: 'text-indigo-200' }
        : { bg: 'bg-white/50', activeBg: 'bg-indigo-500/10', border: 'border-indigo-400/30', activeBorder: 'border-indigo-600', text: 'text-indigo-950', accent: 'text-indigo-700', hover: 'hover:border-indigo-600', secondary: 'text-indigo-800' },
      sky: dark
        ? { bg: 'bg-[#1a1a1a]/50', activeBg: 'bg-sky-500/10', border: 'border-sky-400/30', activeBorder: 'border-sky-400', text: 'text-sky-50', accent: 'text-sky-300', hover: 'hover:border-sky-400', secondary: 'text-sky-200' }
        : { bg: 'bg-white/50', activeBg: 'bg-sky-500/10', border: 'border-sky-400/30', activeBorder: 'border-sky-600', text: 'text-sky-950', accent: 'text-sky-700', hover: 'hover:border-sky-600', secondary: 'text-sky-800' },
      teal: dark
        ? { bg: 'bg-[#1a1a1a]/50', activeBg: 'bg-teal-500/10', border: 'border-teal-400/30', activeBorder: 'border-teal-400', text: 'text-teal-50', accent: 'text-teal-300', hover: 'hover:border-teal-400', secondary: 'text-teal-200' }
        : { bg: 'bg-white/50', activeBg: 'bg-teal-500/10', border: 'border-teal-400/30', activeBorder: 'border-teal-600', text: 'text-teal-950', accent: 'text-teal-700', hover: 'hover:border-teal-600', secondary: 'text-teal-800' },
      lime: dark
        ? { bg: 'bg-[#1a1a1a]/50', activeBg: 'bg-lime-500/10', border: 'border-lime-400/30', activeBorder: 'border-lime-400', text: 'text-lime-50', accent: 'text-lime-300', hover: 'hover:border-lime-400', secondary: 'text-lime-200' }
        : { bg: 'bg-white/50', activeBg: 'bg-lime-500/10', border: 'border-lime-400/30', activeBorder: 'border-lime-600', text: 'text-lime-950', accent: 'text-lime-700', hover: 'hover:border-lime-600', secondary: 'text-lime-800' },
      amber: dark
        ? { bg: 'bg-[#1a1a1a]/50', activeBg: 'bg-amber-500/10', border: 'border-amber-400/30', activeBorder: 'border-amber-400', text: 'text-amber-50', accent: 'text-amber-300', hover: 'hover:border-amber-400', secondary: 'text-amber-200' }
        : { bg: 'bg-white/50', activeBg: 'bg-amber-500/10', border: 'border-amber-400/30', activeBorder: 'border-amber-600', text: 'text-amber-950', accent: 'text-amber-700', hover: 'hover:border-amber-600', secondary: 'text-amber-800' },
      custom: dark
        ? { bg: 'bg-[#1a1a1a]/50', activeBg: 'bg-white/10', border: 'border-white/30', activeBorder: 'border-white', text: 'text-white', accent: 'text-white', hover: 'hover:border-white', secondary: 'text-gray-300' }
        : { bg: 'bg-white/50', activeBg: 'bg-gray-900/10', border: 'border-gray-900/30', activeBorder: 'border-gray-900', text: 'text-gray-900', accent: 'text-gray-900', hover: 'hover:border-gray-900', secondary: 'text-gray-700' },
    };
    return base[theme];
  };

  const colors = getColors(themeColor, isDarkMode);

  return (
    <motion.div
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ delay: index * 0.05 }}
      className={`${isActive ? colors.activeBg : colors.bg} border-2 ${isActive ? colors.activeBorder : colors.border} rounded-lg p-2 mb-1.5 cursor-pointer ${colors.hover} transition-all group backdrop-blur-sm relative`}
      onClick={onSelect}
    >
      <div className="flex items-start justify-between mb-0.5">
        <span 
          className="text-[10px]" 
          style={{ color: getSecondaryTextColor(isDarkMode, themeColor, customColor) }}
        >
          {formattedTime}
        </span>
        <div className="flex items-center gap-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggleFavorite();
            }}
            style={{
              color: conversation.isFavorite 
                ? '#fbbf24' 
                : getIconColor(isDarkMode, themeColor, customColor)
            }}
            className="hover:text-yellow-400 transition-colors"
            title={conversation.isFavorite ? "Bỏ yêu thích" : "Yêu thích"}
          >
            <Star className={`h-3 w-3 ${conversation.isFavorite ? 'fill-current' : ''}`} />
          </button>
          {showDeleteConfirm ? (
            <div className="flex items-center gap-1 bg-red-500/10 rounded px-1.5 py-0.5 border border-red-500/30">
              <span className="text-[9px] text-red-500">Xóa?</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete();
                  toast.success('Đã xóa cuộc trò chuyện');
                }}
                className="text-red-500 hover:text-red-600 text-[9px]"
              >
                ✓
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowDeleteConfirm(false);
                }}
                className="text-gray-500 hover:text-gray-600 text-[9px]"
              >
                ✕
              </button>
            </div>
          ) : (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowDeleteConfirm(true);
              }}
              className={`${isDarkMode ? 'text-gray-600' : 'text-gray-400'} hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100`}
              title="Xóa cuộc trò chuyện"
            >
              <Trash2 className="h-3 w-3" />
            </button>
          )}
        </div>
      </div>
      <p 
        className="text-xs line-clamp-2 mb-0.5 font-medium" 
        style={{ 
          color: isDarkMode ? "#e5e5e5" : "#1a1a1a",
        }}
      >
        {conversation.title}
      </p>
      <div 
        className="text-[10px] font-normal" 
        style={{ 
          color: isDarkMode ? "rgba(255, 255, 255, 0.75)" : "rgba(0, 0, 0, 0.7)",
        }}
      >
        {messageCount} tin nhắn
      </div>
    </motion.div>
  );
}

function formatConversationTimestamp(date: Date): string {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
    return '';
  }
  const now = new Date();
  const diffInMs = now.getTime() - date.getTime();
  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;

  if (diffInMs < minute) return 'Vừa xong';
  if (diffInMs < hour) {
    const minutes = Math.floor(diffInMs / minute);
    return `${minutes} phút trước`;
  }
  if (diffInMs < day) {
    const hours = Math.floor(diffInMs / hour);
    return `${hours} giờ trước`;
  }
  const days = Math.floor(diffInMs / day);
  return `${days} ngày trước`;
}
