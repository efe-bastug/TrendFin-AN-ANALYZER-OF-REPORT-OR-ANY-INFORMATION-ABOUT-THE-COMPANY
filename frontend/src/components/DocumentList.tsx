'use client';

import React from 'react';

interface DocumentListProps {
  currentView?: string;
}

export default function DocumentList({ currentView }: DocumentListProps) {
  if (currentView !== 'documents') {
    return null;
  }

  return (
    <div className="text-center py-12">
      <h3 className="text-lg font-medium text-gray-900 dark:text-white">Documents</h3>
      <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
        Document list will be implemented here.
      </p>
    </div>
  );
}