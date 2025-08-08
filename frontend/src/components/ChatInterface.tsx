'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, FileText, ExternalLink, Loader2 } from 'lucide-react';
import { chatApi, documentApi } from '@/lib/api';
import { ChatMessage, ChatSession, PDFDocument, Citation } from '@/types';

interface ChatInterfaceProps {
  currentView?: string;
}

export default function ChatInterface({ currentView }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [documents, setDocuments] = useState<PDFDocument[]>([]);
  const [selectedDocuments, setSelectedDocuments] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadDocuments();
    loadLastSession();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadDocuments = async () => {
    try {
      const response = await documentApi.getDocuments();
      setDocuments(response.results || []);
    } catch (error) {
      console.error('Failed to load documents:', error);
    }
  };

  const loadLastSession = async () => {
    try {
      const response = await chatApi.getChatSessions();
      const sessions = response.results || [];
      if (sessions.length > 0) {
        const lastSession = sessions[0];
        setCurrentSession(lastSession);
        loadSessionMessages(lastSession.id);
      }
    } catch (error) {
      console.error('Failed to load sessions:', error);
    }
  };

  const loadSessionMessages = async (sessionId: string) => {
    try {
      const response = await chatApi.getSessionMessages(sessionId);
      setMessages(response.results || []);
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  };

  const startNewSession = async () => {
    try {
      const newSession = await chatApi.createChatSession();
      setCurrentSession(newSession);
      setMessages([]);
    } catch (error) {
      console.error('Failed to create session:', error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const question = inputValue.trim();
    setInputValue('');
    setIsLoading(true);

    try {
      let sessionId = currentSession?.id;
      if (!sessionId) {
        const newSession = await chatApi.createChatSession(question);
        setCurrentSession(newSession);
        sessionId = newSession.id;
      }

      const userMessage: ChatMessage = {
        id: `temp-user-${Date.now()}`,
        session: sessionId,
        role: 'user',
        content: question,
        created_at: new Date().toISOString(),
      };
      setMessages(prev => [...prev, userMessage]);

      const response = await chatApi.askQuestion({
        question,
        session_id: sessionId,
        document_ids: selectedDocuments.length > 0 ? selectedDocuments : undefined,
      });

      setMessages(prev => [
        ...prev.filter(m => m.id !== 'temp-user'),
        response.user_message,
        response.assistant_message,
      ]);

    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages(prev => prev.filter(m => m.id !== 'temp-user'));
      
      const errorMessage: ChatMessage = {
        id: 'error-' + Date.now(),
        session: currentSession?.id || '',
        role: 'assistant',
        content: 'Sorry, I encountered an error while processing your question. Please try again.',
        created_at: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDocumentToggle = (documentId: string) => {
    setSelectedDocuments(prev => 
      prev.includes(documentId)
        ? prev.filter(id => id !== documentId)
        : [...prev, documentId]
    );
  };

  const renderMessage = (message: ChatMessage) => {
    const isUser = message.role === 'user';
    
    return (
      <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
        <div className={`flex max-w-3xl ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
          {/* Avatar */}
          <div className={`flex-shrink-0 ${isUser ? 'ml-3' : 'mr-3'}`}>
            <div className={`
              w-8 h-8 rounded-full flex items-center justify-center
              ${isUser 
                ? 'bg-blue-500 text-white' 
                : 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
              }
            `}>
              {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
            </div>
          </div>

          {/* Mesaj içeriği */}
          <div className={`
            rounded-lg px-4 py-2 
            ${isUser 
              ? 'bg-blue-500 text-white' 
              : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100'
            }
          `}>
            <div className="prose prose-sm max-w-none">
              {message.content.split('\n').map((line, index) => (
                <p key={`${message.id}-line-${index}`} className={`
                  ${index === 0 ? 'mt-0' : ''} 
                  ${isUser ? 'text-white' : 'text-gray-900 dark:text-gray-100'}
                `}>
                  {line}
                </p>
              ))}
            </div>

            {/* Kaynaklar */}
            {!isUser && message.citations && message.citations.length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-600">
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Sources:</p>
                <div className="flex flex-wrap gap-2">
                  {message.citations.map((citation, index) => (
                    <CitationBadge key={`citation-${citation.id}-${index}`} citation={citation} index={index + 1} />
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  if (currentView !== 'chat') {
    return null;
  }

  return (
    <div className="flex h-[calc(100vh-12rem)] bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
      {/* Belge seçici yan panel */}
      <div className="w-80 border-r border-gray-200 dark:border-gray-700 flex flex-col">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">Select Documents</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Choose which documents to search (leave empty to search all)
          </p>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4">
          {documents.length === 0 ? (
            <div className="text-center py-8">
              <FileText className="mx-auto h-12 w-12 text-gray-400" />
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                No documents uploaded yet. Upload some PDFs first!
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {documents.map((doc) => (
                <label
                  key={doc.id}
                  className="flex items-center p-3 rounded-lg border border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selectedDocuments.includes(doc.id)}
                    onChange={() => handleDocumentToggle(doc.id)}
                    className="mr-3 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {doc.name}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {doc.processed ? `${doc.chunks_count || 0} chunks` : 'Processing...'}
                    </p>
                  </div>
                </label>
              ))}
            </div>
          )}
        </div>

        {/* Yeni oturum butonu */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={startNewSession}
            className="w-full px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
          >
            New Conversation
          </button>
        </div>
      </div>

      {/* Sohbet alanı */}
      <div className="flex-1 flex flex-col">
        {/* Mesajlar */}
        <div className="flex-1 overflow-y-auto p-4">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <Bot className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-lg font-medium text-gray-900 dark:text-white">
                  Start a conversation
                </h3>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Ask questions about your uploaded PDF documents
                </p>
              </div>
            </div>
          ) : (
            <>
              {messages.map((message, idx) => (
                <div key={message.id || idx}>
                  {renderMessage(message)}
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start mb-4">
                  <div className="flex">
                    <div className="flex-shrink-0 mr-3">
                      <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center">
                        <Bot className="w-4 h-4 text-gray-600 dark:text-gray-300" />
                      </div>
                    </div>
                    <div className="bg-gray-100 dark:bg-gray-800 rounded-lg px-4 py-2">
                      <Loader2 className="w-5 h-5 animate-spin text-gray-500" />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Girdi formu */}
        <div className="border-t border-gray-200 dark:border-gray-700 p-4">
          <form onSubmit={handleSubmit} className="flex space-x-4">
            <div className="flex-1">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Ask a question about your documents..."
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                disabled={isLoading}
              />
            </div>
            <button
              type="submit"
              disabled={!inputValue.trim() || isLoading}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Send className="w-5 h-5" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

// Kaynak rozet bileşeni
function CitationBadge({ citation, index }: { citation: Citation; index: number }) {
  const handleClick = () => {
    // TODO: Vurgulanmış sayfayla PDF görüntüleyiciyi aç
    console.log('Open PDF:', citation.document_id, 'page:', citation.page_start);
  };

  return (
    <button
      onClick={handleClick}
      className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors"
    >
      <FileText className="w-3 h-3 mr-1" />
      [{index}] {citation.document_name}
      <ExternalLink className="w-3 h-3 ml-1" />
    </button>
  );
}