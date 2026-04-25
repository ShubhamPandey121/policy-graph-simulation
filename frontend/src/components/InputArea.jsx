import React, { useState, useRef, useEffect } from 'react';
import { Paperclip, Send, X, FileText } from 'lucide-react';

export default function InputArea({ onSubmit, isLoading }) {
  const [query, setQuery] = useState('');
  const [files, setFiles] = useState([]);
  const fileInputRef = useRef(null);
  const textareaRef = useRef(null);

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files);
    const validFiles = selectedFiles.filter(f => 
      f.type === 'application/pdf' || f.type === 'text/plain' || f.type.startsWith('image/')
    );
    setFiles([...files, ...validFiles]);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const removeFile = (index) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.currentTarget.classList.add('dragging');
  };

  const handleDragLeave = (e) => {
    e.currentTarget.classList.remove('dragging');
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.currentTarget.classList.remove('dragging');
    const droppedFiles = Array.from(e.dataTransfer.files);
    const validFiles = droppedFiles.filter(f => 
      f.type === 'application/pdf' || f.type === 'text/plain' || f.type.startsWith('image/')
    );
    setFiles([...files, ...validFiles]);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!query.trim() && files.length === 0) return;
    if (isLoading) return;
    
    onSubmit(query.trim(), files);
    setQuery('');
    setFiles([]);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleInput = (e) => {
    setQuery(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 128) + 'px';
  };

  return (
    <div className="input-area">
      <div className="input-container">
        {files.length > 0 && (
          <div className="file-attachments">
            {files.map((file, i) => (
              <div className="file-attachment" key={i}>
                <FileText size={14} />
                <span>{file.name}</span>
                <button type="button" className="file-remove" onClick={() => removeFile(i)}>
                  <X size={14} />
                </button>
              </div>
            ))}
          </div>
        )}

        <form className="chat-form" onSubmit={handleSubmit}>
          <div 
            className="input-wrapper" 
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <textarea 
              ref={textareaRef}
              value={query}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              placeholder="Ask about policy impacts, upload documents for analysis..."
              rows={1}
              disabled={isLoading}
            ></textarea>

            <div className="input-actions">
              <input 
                type="file" 
                ref={fileInputRef} 
                accept=".pdf,.txt,image/*" 
                multiple 
                hidden 
                onChange={handleFileSelect} 
              />
              <button 
                type="button" 
                className="action-btn" 
                onClick={() => fileInputRef.current?.click()}
                disabled={isLoading}
              >
                <Paperclip size={18} />
              </button>
              <button 
                type="submit" 
                className="send-btn"
                disabled={isLoading || (!query.trim() && files.length === 0)}
              >
                <Send size={18} />
              </button>
            </div>
          </div>
        </form>

        <p className="input-hint">
          AI-powered policy simulation • Upload PDFs or images for analysis
        </p>
      </div>
    </div>
  );
}
