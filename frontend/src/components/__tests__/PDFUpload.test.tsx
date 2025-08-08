import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import PDFUpload from '../PDFUpload'

jest.mock('@/lib/api', () => ({
  documentApi: {
    uploadDocument: jest.fn(),
    getDocumentStatus: jest.fn(),
  },
}))

describe('PDFUpload', () => {
  const mockOnUploadComplete = jest.fn()
  const mockOnUploadError = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders upload area', () => {
    render(
      <PDFUpload
        onUploadComplete={mockOnUploadComplete}
        onUploadError={mockOnUploadError}
      />
    )

    expect(screen.getByText(/drag & drop/i)).toBeInTheDocument()
    expect(screen.getByText(/or click to browse/i)).toBeInTheDocument()
  })

  it('shows file size limit', () => {
    render(
      <PDFUpload
        onUploadComplete={mockOnUploadComplete}
        onUploadError={mockOnUploadError}
        maxSizeMB={15}
      />
    )

    expect(screen.getByText(/max 15MB/i)).toBeInTheDocument()
  })

  it('shows max files limit', () => {
    render(
      <PDFUpload
        onUploadComplete={mockOnUploadComplete}
        onUploadError={mockOnUploadError}
        maxFiles={10}
      />
    )

    expect(screen.getByText(/max 10 files/i)).toBeInTheDocument()
  })

  it('calls onUploadError for non-PDF files', () => {
    render(
      <PDFUpload
        onUploadComplete={mockOnUploadComplete}
        onUploadError={mockOnUploadError}
      />
    )

    const file = new File(['test content'], 'test.txt', { type: 'text/plain' })
    const dropzone = screen.getByTestId('dropzone')

    fireEvent.drop(dropzone, {
      dataTransfer: {
        files: [file],
      },
    })

    expect(mockOnUploadError).toHaveBeenCalledWith('test.txt is not a PDF file')
  })

  it('calls onUploadError for oversized files', () => {
    render(
      <PDFUpload
        onUploadComplete={mockOnUploadComplete}
        onUploadError={mockOnUploadError}
        maxSizeMB={1}
      />
    )

    const largeFile = new File(['x'.repeat(2 * 1024 * 1024)], 'large.pdf', {
      type: 'application/pdf',
    })
    const dropzone = screen.getByTestId('dropzone')

    fireEvent.drop(dropzone, {
      dataTransfer: {
        files: [largeFile],
      },
    })

    expect(mockOnUploadError).toHaveBeenCalledWith('large.pdf is larger than 1MB')
  })

  it('accepts valid PDF files', () => {
    const { documentApi } = require('@/lib/api')
    documentApi.uploadDocument.mockResolvedValue({
      id: 'test-id',
      name: 'test.pdf',
      size: 1024,
    })

    render(
      <PDFUpload
        onUploadComplete={mockOnUploadComplete}
        onUploadError={mockOnUploadError}
      />
    )

    const file = new File(['test content'], 'test.pdf', {
      type: 'application/pdf',
    })
    const dropzone = screen.getByTestId('dropzone')

    fireEvent.drop(dropzone, {
      dataTransfer: {
        files: [file],
      },
    })

    expect(documentApi.uploadDocument).toHaveBeenCalledWith(file)
  })
}) 