'use client';

import React, { useState } from 'react';
import { Upload, MessageSquare, FileText, Menu, X, Sun, Moon } from 'lucide-react';

interface MainLayoutProps {
  children: React.ReactNode;
}

export default function MainLayout({ children }: MainLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [currentView, setCurrentView] = useState<'upload' | 'chat' | 'documents'>('upload');

  const toggleDarkMode = () => {
    setDarkMode(!darkMode);
    if (!darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  };

  const navigation = [
    {
      name: 'Upload PDFs',
      href: '#',
      icon: Upload,
      view: 'upload' as const,
      current: currentView === 'upload',
    },
    {
      name: 'Chat & Q&A',
      href: '#',
      icon: MessageSquare,
      view: 'chat' as const,
      current: currentView === 'chat',
    },
    {
      name: 'Documents',
      href: '#',
      icon: FileText,
      view: 'documents' as const,
      current: currentView === 'documents',
    },
  ];

  return (
    <div className={`min-h-screen ${darkMode ? 'dark' : ''}`}>
      <div className="bg-white dark:bg-gray-900 transition-colors">
        {/* Mobil yan menü örtüsü */}
        {sidebarOpen && (
          <div className="fixed inset-0 z-40 lg:hidden">
            <div className="fixed inset-0 bg-gray-600 bg-opacity-75" onClick={() => setSidebarOpen(false)} />
            <div className="fixed inset-y-0 left-0 flex w-full max-w-xs flex-col bg-white dark:bg-gray-800">
              <div className="flex h-16 items-center justify-between px-4">
                <h1 className="text-xl font-bold text-gray-900 dark:text-white">PDF Q&A</h1>
                <button
                  onClick={() => setSidebarOpen(false)}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  <X className="h-6 w-6" />
                </button>
              </div>
              <nav className="flex-1 space-y-1 px-2 py-4">
                {navigation.map((item) => (
                  <button
                    key={item.name}
                    onClick={() => {
                      setCurrentView(item.view);
                      setSidebarOpen(false);
                    }}
                    className={`
                      group flex w-full items-center rounded-md px-2 py-2 text-sm font-medium transition-colors
                      ${item.current
                        ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                        : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700'
                      }
                    `}
                  >
                    <item.icon className="mr-3 h-5 w-5" />
                    {item.name}
                  </button>
                ))}
              </nav>
            </div>
          </div>
        )}

        {/* Desktop sidebar */}
        <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col">
          <div className="flex flex-col flex-grow bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between h-16 px-4 border-b border-gray-200 dark:border-gray-700">
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">PDF Q&A</h1>
              <button
                onClick={toggleDarkMode}
                className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-md"
              >
                {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
              </button>
            </div>
            <nav className="flex-1 space-y-1 px-2 py-4">
              {navigation.map((item) => (
                <button
                  key={item.name}
                  onClick={() => setCurrentView(item.view)}
                  className={`
                    group flex w-full items-center rounded-md px-2 py-2 text-sm font-medium transition-colors
                    ${item.current
                      ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                      : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700'
                    }
                  `}
                >
                  <item.icon className="mr-3 h-5 w-5" />
                  {item.name}
                </button>
              ))}
            </nav>
            
            {/* Footer info */}
            <div className="p-4 border-t border-gray-200 dark:border-gray-700">
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Upload PDFs and ask questions using AI-powered search
              </p>
            </div>
          </div>
        </div>

        {/* Main content */}
        <div className="lg:pl-64">
          {/* Mobil için üst çubuk */}
          <div className="sticky top-0 z-10 lg:hidden bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between h-16 px-4">
              <button
                onClick={() => setSidebarOpen(true)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <Menu className="h-6 w-6" />
              </button>
              <h1 className="text-lg font-medium text-gray-900 dark:text-white">
                {navigation.find(item => item.current)?.name}
              </h1>
              <button
                onClick={toggleDarkMode}
                className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-md"
              >
                {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
              </button>
            </div>
          </div>

          {/* Page content */}
          <main className="flex-1">
            <div className="py-6">
              <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
                {/* Sayfa başlığı */}
                <div className="mb-8">
                  <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                    {currentView === 'upload' && 'Upload PDF Documents'}
                    {currentView === 'chat' && 'Chat & Ask Questions'}
                    {currentView === 'documents' && 'Document Library'}
                  </h1>
                  <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                    {currentView === 'upload' && 'Upload your PDF documents to start asking questions'}
                    {currentView === 'chat' && 'Ask questions about your uploaded documents'}
                    {currentView === 'documents' && 'Manage your uploaded PDF documents'}
                  </p>
                </div>

                {/* Mevcut görünüme göre dinamik içerik */}
                {React.cloneElement(children as React.ReactElement, { currentView })}
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}