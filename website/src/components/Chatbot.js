import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChatBubbleLeftRightIcon,
  XMarkIcon,
  PaperAirplaneIcon,
  SparklesIcon,
  UserIcon,
  CpuChipIcon,
} from '@heroicons/react/24/outline';

const Chatbot = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'bot',
      content: 'Hello! I\'m your AI Surveillance Assistant. I can help you with system monitoring, camera management, alert analysis, and technical questions. How can I assist you today?',
      timestamp: new Date(),
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const suggestedQuestions = [
    "How do I add a new camera?",
    "What are the current system alerts?",
    "How to configure motion detection?",
    "Show me system performance metrics",
    "Help with camera offline issues",
    "Explain AI detection confidence scores"
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  const simulateTyping = () => {
    setIsTyping(true);
    return new Promise(resolve => {
      setTimeout(() => {
        setIsTyping(false);
        resolve();
      }, 1000 + Math.random() * 2000);
    });
  };

  const getAIResponse = async (message) => {
    // In production, this would connect to your RAG service
    // For now, providing intelligent responses based on message content
    const lowerMessage = message.toLowerCase();
    
    if (lowerMessage.includes('camera') || lowerMessage.includes('add')) {
      return {
        type: 'bot',
        content: '🎥 **Camera Management**\n\nTo add a new camera:\n1. Navigate to the **Cameras** page\n2. Click **"Add Camera"**\n3. Enter camera details (IP, credentials, location)\n4. Configure detection zones and sensitivity\n5. Test connection and save\n\nNeed help with a specific camera brand or connection issue?',
        metadata: { category: 'camera_management' }
      };
    }
    
    if (lowerMessage.includes('alert') || lowerMessage.includes('notification')) {
      return {
        type: 'bot',
        content: '🚨 **Alert System**\n\nI can help you with:\n• **Current Alerts**: View active security alerts\n• **Alert Rules**: Configure when to trigger notifications\n• **Severity Levels**: Understand High/Medium/Low priorities\n• **Notification Channels**: Email, SMS, webhook setup\n\nYou currently have **3 active alerts** that need attention. Would you like me to show them?',
        metadata: { category: 'alerts' }
      };
    }
    
    if (lowerMessage.includes('performance') || lowerMessage.includes('metric') || lowerMessage.includes('system')) {
      return {
        type: 'bot',
        content: '📊 **System Performance**\n\n**Current Status:**\n• **Uptime**: 99.2% (7 days)\n• **Active Cameras**: 12/15 online\n• **Storage**: 2.3TB used / 5TB total\n• **CPU Usage**: 45% avg\n• **Memory**: 6.2GB / 16GB\n\n**Quick Actions:**\n- View detailed analytics\n- Check offline cameras\n- Storage optimization tips',
        metadata: { category: 'performance' }
      };
    }
    
    if (lowerMessage.includes('offline') || lowerMessage.includes('connection') || lowerMessage.includes('troubleshoot')) {
      return {
        type: 'bot',
        content: '🔧 **Connection Troubleshooting**\n\n**Common solutions for offline cameras:**\n\n1. **Network Check**: Verify camera IP and network connectivity\n2. **Credentials**: Ensure username/password are correct\n3. **Firewall**: Check firewall settings and port access\n4. **Power**: Verify camera power and LED status\n5. **Firmware**: Update camera firmware if needed\n\n**Currently offline**: Camera-07 (Parking Lot) - Last seen 2 hours ago. Need specific help with this camera?',
        metadata: { category: 'troubleshooting' }
      };
    }
    
    if (lowerMessage.includes('ai') || lowerMessage.includes('detection') || lowerMessage.includes('confidence')) {
      return {
        type: 'bot',
        content: '🤖 **AI Detection System**\n\n**Confidence Scores Explained:**\n• **90-100%**: High confidence - Action recommended\n• **70-89%**: Medium confidence - Review suggested\n• **50-69%**: Low confidence - Manual verification needed\n\n**Current AI Performance:**\n• **Person Detection**: 94% accuracy\n• **Vehicle Detection**: 91% accuracy\n• **Anomaly Detection**: 87% accuracy\n\nThe AI continuously learns from your feedback to improve accuracy.',
        metadata: { category: 'ai_detection' }
      };
    }
    
    if (lowerMessage.includes('help') || lowerMessage.includes('support') || lowerMessage.includes('how')) {
      return {
        type: 'bot',
        content: '💡 **I\'m here to help!**\n\nI can assist you with:\n\n🎥 **Camera Management** - Setup, configuration, troubleshooting\n🚨 **Alert System** - Rules, notifications, severity levels\n📊 **Analytics** - Performance metrics, system health\n🔧 **Technical Support** - Connection issues, optimization\n🤖 **AI Features** - Detection settings, confidence scores\n📚 **Documentation** - Guides, API references\n\nJust ask me anything or click on a suggested question below!',
        metadata: { category: 'general_help' }
      };
    }
    
    // Default response for unrecognized queries
    return {
      type: 'bot',
      content: '🤔 I understand you\'re asking about surveillance system features. While I can help with camera management, alerts, system performance, and troubleshooting, I might need more context for your specific question.\n\nCould you try rephrasing your question or choose from the suggested topics below? I\'m continuously learning to better assist you!',
      metadata: { category: 'clarification' }
    };
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMessage = {
      id: messages.length + 1,
      type: 'user',
      content: inputMessage,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');

    // Simulate AI thinking
    await simulateTyping();

    // Get AI response
    const aiResponse = await getAIResponse(inputMessage);
    const botMessage = {
      id: messages.length + 2,
      ...aiResponse,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, botMessage]);
  };

  const handleSuggestedQuestion = async (question) => {
    setInputMessage(question);
    
    const userMessage = {
      id: messages.length + 1,
      type: 'user',
      content: question,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');

    await simulateTyping();

    const aiResponse = await getAIResponse(question);
    const botMessage = {
      id: messages.length + 2,
      ...aiResponse,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, botMessage]);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <>
      {/* Chatbot Toggle Button */}
      <motion.button
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 z-50 bg-gradient-to-r from-blue-600 to-cyan-600 text-white p-4 rounded-full shadow-lg hover:shadow-xl transition-all duration-300"
      >
        <AnimatePresence mode="wait">
          {isOpen ? (
            <motion.div
              key="close"
              initial={{ rotate: 180, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: 180, opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <XMarkIcon className="h-6 w-6" />
            </motion.div>
          ) : (
            <motion.div
              key="chat"
              initial={{ rotate: -180, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: -180, opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <ChatBubbleLeftRightIcon className="h-6 w-6" />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.button>

      {/* Chatbot Window */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 100, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 100, scale: 0.9 }}
            transition={{ type: "spring", damping: 20, stiffness: 300 }}
            className="fixed bottom-24 right-6 z-40 w-96 h-[600px] bg-white dark:bg-slate-800 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 flex flex-col overflow-hidden"
          >
            {/* Header */}
            <div className="bg-gradient-to-r from-blue-600 to-cyan-600 text-white p-4 flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="relative">
                  <CpuChipIcon className="h-8 w-8" />
                  <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
                </div>
                <div>
                  <h3 className="font-semibold">AI Assistant</h3>
                  <p className="text-xs text-blue-100">Surveillance System Support</p>
                </div>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1 hover:bg-white/20 rounded-lg transition-colors"
              >
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50 dark:bg-slate-900">
              {messages.map((message) => (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`flex items-start space-x-2 max-w-[80%] ${message.type === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}>
                    <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                      message.type === 'user' 
                        ? 'bg-blue-600 text-white' 
                        : 'bg-gradient-to-br from-purple-500 to-blue-600 text-white'
                    }`}>
                      {message.type === 'user' ? (
                        <UserIcon className="h-5 w-5" />
                      ) : (
                        <SparklesIcon className="h-5 w-5" />
                      )}
                    </div>
                    <div className={`rounded-2xl p-3 ${
                      message.type === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-sm border border-slate-200 dark:border-slate-700'
                    }`}>
                      <div className="whitespace-pre-wrap text-sm leading-relaxed">
                        {message.content}
                      </div>
                      <div className={`text-xs mt-2 opacity-70 ${
                        message.type === 'user' ? 'text-blue-100' : 'text-slate-500'
                      }`}>
                        {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))}

              {/* Typing Indicator */}
              {isTyping && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex justify-start"
                >
                  <div className="flex items-start space-x-2">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-600 text-white flex items-center justify-center">
                      <SparklesIcon className="h-5 w-5" />
                    </div>
                    <div className="bg-white dark:bg-slate-800 rounded-2xl p-3 shadow-sm border border-slate-200 dark:border-slate-700">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce delay-100"></div>
                        <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce delay-200"></div>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Suggested Questions */}
            {messages.length <= 1 && (
              <div className="p-4 bg-white dark:bg-slate-800 border-t border-slate-200 dark:border-slate-700">
                <p className="text-sm text-slate-600 dark:text-slate-400 mb-3">Try asking:</p>
                <div className="space-y-2">
                  {suggestedQuestions.slice(0, 3).map((question, index) => (
                    <button
                      key={index}
                      onClick={() => handleSuggestedQuestion(question)}
                      className="w-full text-left text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100 dark:hover:bg-blue-900/40 rounded-lg p-2 transition-colors"
                    >
                      {question}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Input */}
            <div className="p-4 bg-white dark:bg-slate-800 border-t border-slate-200 dark:border-slate-700">
              <div className="flex space-x-2">
                <textarea
                  ref={inputRef}
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask about cameras, alerts, or system help..."
                  className="flex-1 resize-none border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 placeholder-slate-500 dark:placeholder-slate-400"
                  rows="1"
                  style={{ minHeight: '40px', maxHeight: '120px' }}
                />
                <button
                  onClick={handleSendMessage}
                  disabled={!inputMessage.trim() || isTyping}
                  className="flex-shrink-0 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white p-2 rounded-lg transition-colors"
                >
                  <PaperAirplaneIcon className="h-5 w-5" />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default Chatbot;