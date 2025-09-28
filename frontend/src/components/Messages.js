import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useWebSocket } from '../contexts/WebSocketContext';
import GlassCard from './ui/GlassCard';
import { MessageSquare, Send, User, Clock } from 'lucide-react';

const Messages = () => {
  const { t } = useTranslation();
  const { subscribe, isConnected } = useWebSocket();
  const [messages, setMessages] = useState([]);
  const [stats, setStats] = useState({
    total_messages: 0,
    messages_today: 0,
    active_conversations: 0
  });
  const [loading, setLoading] = useState(true);
  const [selectedMessage, setSelectedMessage] = useState(null);

  useEffect(() => {
    fetchMessages();
    fetchStats();
  }, []);

  // Subscribe to real-time message updates
  useEffect(() => {
    const unsubscribeNewMessage = subscribe('new_message', (message) => {
      // Transform incoming message data
      const transformedMessage = {
        id: message.data.id || Date.now(),
        sender_id: message.data.sender_id,
        sender_name: message.data.sender_name || message.data.sender_id,
        recipient_id: message.data.receiver_id,
        recipient_name: message.data.recipient_name || message.data.receiver_id,
        content: message.data.text || message.data.content,
        message_type: message.data.direction === 'outgoing' ? 'sent' : 'received',
        created_at: message.data.timestamp || new Date().toISOString(),
        is_bot_response: message.data.is_bot_response || false
      };
      setMessages(prev => [transformedMessage, ...prev.slice(0, 49)]); // Keep last 50 messages
      setStats(prev => ({
        ...prev,
        total_messages: prev.total_messages + 1,
        messages_today: prev.messages_today + 1
      }));
    });

    const unsubscribeStatsUpdate = subscribe('statistics_update', (message) => {
      if (message.data.message_stats) {
        setStats(prev => ({
          ...prev,
          ...message.data.message_stats
        }));
      }
    });

    return () => {
      unsubscribeNewMessage();
      unsubscribeStatsUpdate();
    };
  }, [subscribe]);

  const fetchMessages = async () => {
    try {
      const response = await fetch('/api/messages/?limit=50&offset=0');
      const data = await response.json();
      // Transform backend data to match frontend expectations
      const transformedMessages = (data.messages || []).map(msg => ({
        id: msg.id,
        sender_id: msg.sender_id,
        sender_name: msg.sender_id, // Use ID as name for now
        recipient_id: msg.receiver_id,
        recipient_name: msg.receiver_id, // Use ID as name for now
        content: msg.text,
        message_type: msg.direction === 'outgoing' ? 'sent' : 'received',
        created_at: msg.timestamp,
        is_bot_response: false // Default to false
      }));
      setMessages(transformedMessages);
    } catch (error) {
      console.error('Error fetching messages:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/messages/stats/overview');
      const data = await response.json();
      setStats(prev => ({
        ...prev,
        ...data
      }));
    } catch (error) {
      console.error('Error fetching message stats:', error);
    }
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString();
  };

  const getMessageTypeColor = (messageType) => {
    const colors = {
      text: 'text-blue-400',
      location: 'text-green-400',
      alert: 'text-red-400',
      command: 'text-purple-400',
      system: 'text-gray-400'
    };
    return colors[messageType] || 'text-gray-400';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent-cyan"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-white">{t('messages.monitoring')}</h1>
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}></div>
          <span className="text-sm text-gray-400">
            {isConnected ? t('messages.live_updates') : t('status.disconnected')}
          </span>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <GlassCard className="text-center">
          <MessageSquare className="w-8 h-8 text-accent-cyan mx-auto mb-2" />
          <div className="text-2xl font-bold text-white">{stats.total_messages}</div>
          <div className="text-sm text-gray-400">{t('messages.total_messages')}</div>
        </GlassCard>

        <GlassCard className="text-center">
          <Send className="w-8 h-8 text-accent-green mx-auto mb-2" />
          <div className="text-2xl font-bold text-white">{stats.messages_today}</div>
          <div className="text-sm text-gray-400">{t('messages.messages_today')}</div>
        </GlassCard>

        <GlassCard className="text-center">
          <User className="w-8 h-8 text-accent-purple mx-auto mb-2" />
          <div className="text-2xl font-bold text-white">{stats.active_conversations}</div>
          <div className="text-sm text-gray-400">{t('messages.active_conversations')}</div>
        </GlassCard>
      </div>

      {/* Messages List */}
      <GlassCard title={t('messages.recent_messages')}>
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {messages.map((message) => (
            <div
              key={message.id}
              className="p-4 bg-dark-800/30 rounded-lg border border-dark-600 hover:border-accent-cyan/30 transition-colors cursor-pointer"
              onClick={() => setSelectedMessage(message)}
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <h3 className="font-semibold text-white">{message.sender_name || t('messages.unknown')}</h3>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getMessageTypeColor(message.message_type)} bg-current/20`}>
                      {message.message_type?.toUpperCase()}
                    </span>
                    {message.is_bot_response && (
                      <span className="px-2 py-1 bg-purple-600 text-white rounded-full text-xs">
                        {t('messages.bot')}
                      </span>
                    )}
                  </div>
                  <p className="text-gray-300 text-sm mb-2 line-clamp-2">{message.content}</p>
                  <div className="flex items-center space-x-4 text-xs text-gray-400">
                    <span>{t('messages.to')}: {message.recipient_name || message.recipient_id}</span>
                    <span className="flex items-center space-x-1">
                      <Clock className="w-3 h-3" />
                      {formatTimestamp(message.created_at)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
          {messages.length === 0 && (
            <p className="text-gray-400 text-center py-8">{t('messages.no_messages')}</p>
          )}
        </div>
      </GlassCard>

      {/* Message Details Modal */}
      {selectedMessage && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <GlassCard className="w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-start mb-4">
              <h2 className="text-xl font-bold text-white">{t('messages.details')}</h2>
              <button
                onClick={() => setSelectedMessage(null)}
                className="text-gray-400 hover:text-white"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('messages.from')}</label>
                  <p className="text-white">{selectedMessage.sender_name || selectedMessage.sender_id}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('messages.to_label')}</label>
                  <p className="text-white">{selectedMessage.recipient_name || selectedMessage.recipient_id}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('messages.type')}</label>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getMessageTypeColor(selectedMessage.message_type)} bg-current/20`}>
                    {selectedMessage.message_type?.toUpperCase()}
                  </span>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('messages.timestamp')}</label>
                  <p className="text-white">{formatTimestamp(selectedMessage.created_at)}</p>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">{t('messages.content')}</label>
                <p className="text-white bg-dark-800/50 p-3 rounded whitespace-pre-wrap">{selectedMessage.content}</p>
              </div>

              {selectedMessage.metadata && (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('messages.metadata')}</label>
                  <pre className="text-xs text-gray-400 bg-dark-800/50 p-3 rounded overflow-x-auto">
                    {JSON.stringify(selectedMessage.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
};

export default Messages;