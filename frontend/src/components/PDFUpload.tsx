'use client';

import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, File, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { documentApi } from '@/lib/api';
import { PDFDocument, UploadProgress } from '@/types';

interface PDFUploadProps {
  onUploadComplete?: (documents: PDFDocument[]) => void;
  onUploadError?: (error: string) => void;
  maxFiles?: number;
  maxSizeMB?: number;
}

export default function PDFUpload({
  onUploadComplete,
  onUploadError,
  maxFiles = 10,
  maxSizeMB = 15,
}: PDFUploadProps) {
  const [uploads, setUploads] = useState<UploadProgress[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const validFiles = acceptedFiles.filter(file => {
      if (file.type !== 'application/pdf') {
        onUploadError?.(`${file.name} is not a PDF file`);
        return false;
      }
      if (file.size > maxSizeMB * 1024 * 1024) {
        onUploadError?.(`${file.name} is larger than ${maxSizeMB}MB`);
        return false;
      }
      return true;
    });

    if (validFiles.length === 0) return;

    const newUploads: UploadProgress[] = validFiles.map(file => ({
      file,
      progress: 0,
      status: 'pending',
    }));

    setUploads(prev => [...prev, ...newUploads]);
    setIsUploading(true);

    try {
      if (validFiles.length === 1) {
        await uploadSingleFile(validFiles[0], newUploads[0]);
      } else {
        await uploadMultipleFiles(validFiles, newUploads);
      }
    } catch (error) {
      console.error('Upload error:', error);
      onUploadError?.(error instanceof Error ? error.message : 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  }, [maxSizeMB, onUploadError]);

  const uploadSingleFile = async (file: File, uploadProgress: UploadProgress) => {
    try {
      setUploads(prev => prev.map(u => 
        u.file === file ? { ...u, status: 'uploading', progress: 0 } : u
      ));

      const progressInterval = setInterval(() => {
        setUploads(prev => prev.map(u => 
          u.file === file && u.progress < 90 
            ? { ...u, progress: u.progress + 10 } 
            : u
        ));
      }, 200);

      const document = await documentApi.uploadDocument(file);

      clearInterval(progressInterval);

      setUploads(prev => prev.map(u => 
        u.file === file 
          ? { ...u, status: 'processing', progress: 100, document } 
          : u
      ));

      await pollProcessingStatus(document.id, file);

    } catch (error) {
      setUploads(prev => prev.map(u => 
        u.file === file 
          ? { ...u, status: 'error', error: error instanceof Error ? error.message : 'Upload failed' } 
          : u
      ));
      throw error;
    }
  };

  const uploadMultipleFiles = async (files: File[], uploadProgresses: UploadProgress[]) => {
    try {
      setUploads(prev => prev.map(u => 
        files.includes(u.file) ? { ...u, status: 'uploading', progress: 50 } : u
      ));

      const result = await documentApi.uploadMultipleDocuments(files);

      result.uploaded.forEach((document, index) => {
        const file = files[index];
        setUploads(prev => prev.map(u => 
          u.file === file 
            ? { ...u, status: 'processing', progress: 100, document } 
            : u
        ));

        // İşleme durumunu kontrol et
        pollProcessingStatus(document.id, file);
      });

      // Hataları ele al
      result.errors.forEach(error => {
        console.error('Upload error:', error);
        onUploadError?.(error.filename + ': ' + JSON.stringify(error.errors));
      });

    } catch (error) {
      setUploads(prev => prev.map(u => 
        files.includes(u.file) 
          ? { ...u, status: 'error', error: error instanceof Error ? error.message : 'Upload failed' } 
          : u
      ));
      throw error;
    }
  };

  const pollProcessingStatus = async (documentId: string, file: File) => {
    const maxAttempts = 60;
    let attempts = 0;

    const poll = async () => {
      try {
        const document = await documentApi.getDocument(documentId);
        
        setUploads(prev => prev.map(u => 
          u.file === file ? { ...u, document } : u
        ));

        if (document.processed) {
          setUploads(prev => prev.map(u => 
            u.file === file ? { ...u, status: 'completed' } : u
          ));
          
          onUploadComplete?.([document]);
          return;
        }

        if (document.processing_status === 'failed') {
          setUploads(prev => prev.map(u => 
            u.file === file ? { ...u, status: 'error', error: 'Processing failed' } : u
          ));
          return;
        }

        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000);
        } else {
          setUploads(prev => prev.map(u => 
            u.file === file ? { ...u, status: 'error', error: 'Processing timeout' } : u
          ));
        }
      } catch (error) {
        console.error('Polling error:', error);
        setUploads(prev => prev.map(u => 
          u.file === file ? { ...u, status: 'error', error: 'Failed to check status' } : u
        ));
      }
    };

    setTimeout(poll, 2000);
  };

  const removeUpload = (file: File) => {
    setUploads(prev => prev.filter(u => u.file !== file));
  };

  const clearCompleted = () => {
    setUploads(prev => prev.filter(u => u.status !== 'completed'));
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    maxFiles,
    maxSize: maxSizeMB * 1024 * 1024,
    disabled: isUploading,
  });

  const getStatusIcon = (status: UploadProgress['status']) => {
    switch (status) {
      case 'uploading':
      case 'processing':
        return <Loader2 className="w-5 h-5 animate-spin text-blue-500" />;
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return <File className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusText = (upload: UploadProgress) => {
    switch (upload.status) {
      case 'pending':
        return 'Pending';
      case 'uploading':
        return `Uploading... ${upload.progress}%`;
      case 'processing':
        return 'Processing PDF...';
      case 'completed':
        return `Completed (${upload.document?.chunks_count || 0} chunks)`;
      case 'error':
        return `Error: ${upload.error}`;
      default:
        return 'Unknown';
    }
  };

  return (
    <div className="w-full space-y-6">
      {/* Bırakma Alanı */}
      <div
        {...getRootProps()}
        data-testid="dropzone"
        className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
          ${isDragActive 
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
            : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
          }
          ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} />
        
        <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
        
        <div className="space-y-2">
          <p className="text-lg font-medium text-gray-900 dark:text-gray-100">
            {isDragActive ? 'Drop PDF files here...' : 'Upload PDF documents'}
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Drag and drop PDF files here, or click to select files
          </p>
          <p className="text-xs text-gray-400 dark:text-gray-500">
            Maximum {maxFiles} files, {maxSizeMB}MB each
          </p>
        </div>
      </div>

      {/* Yükleme İlerlemesi */}
      {uploads.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
              Upload Progress
            </h3>
            {uploads.some(u => u.status === 'completed') && (
              <button
                onClick={clearCompleted}
                className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
              >
                Clear completed
              </button>
            )}
          </div>

          <div className="space-y-3">
            {uploads.map((upload) => (
              <div
                key={upload.file.name + upload.file.lastModified}
                className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg"
              >
                <div className="flex items-center space-x-3 flex-1">
                  {getStatusIcon(upload.status)}
                  
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                      {upload.file.name}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {getStatusText(upload)}
                    </p>
                    
                    {/* İlerleme Çubuğu */}
                    {(upload.status === 'uploading' || upload.status === 'processing') && (
                      <div className="mt-2 w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <div
                          className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${upload.progress}%` }}
                        />
                      </div>
                    )}
                  </div>
                </div>

                <button
                  onClick={() => removeUpload(upload.file)}
                  className="ml-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  disabled={upload.status === 'uploading' || upload.status === 'processing'}
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}