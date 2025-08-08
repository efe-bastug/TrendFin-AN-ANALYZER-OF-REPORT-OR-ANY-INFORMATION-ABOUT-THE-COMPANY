'use client';

import React from 'react';
import MainLayout from '@/components/MainLayout';
import PDFUpload from '@/components/PDFUpload';
import ChatInterface from '@/components/ChatInterface';
import DocumentList from '@/components/DocumentList';

interface PageContentProps {
  currentView: 'upload' | 'chat' | 'documents';
}

function PageContent({ currentView }: PageContentProps) {
  const handleUploadComplete = (documents: any[]) => {
    console.log('Upload completed:', documents);
  };

  const handleUploadError = (error: string) => {
    console.error('Upload error:', error);
  };

  return (
    <div className="space-y-6">
      {/* Yükleme Görünümü */}
      {currentView === 'upload' && (
        <div className="max-w-4xl mx-auto">
          <PDFUpload
            onUploadComplete={handleUploadComplete}
            onUploadError={handleUploadError}
            maxFiles={10}
            maxSizeMB={15}
          />
        </div>
      )}

      {/* Sohbet Görünümü */}
      {currentView === 'chat' && (
        <div className="max-w-7xl mx-auto">
          <ChatInterface currentView={currentView} />
        </div>
      )}

      {/* Belgeler Görünümü */}
      {currentView === 'documents' && (
        <div className="max-w-6xl mx-auto">
          <DocumentList currentView={currentView} />
        </div>
      )}
    </div>
  );
}

export default function Home() {
  return (
    <MainLayout>
      <PageContent currentView="upload" />
    </MainLayout>
  );
}