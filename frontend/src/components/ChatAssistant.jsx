import React, { useState, useEffect, useRef } from 'react';
import { Bot, User, X, Send } from 'lucide-react';
import axios from 'axios';

const API_URL = 'http://localhost:8000';

export default function ChatAssistant({ isOpen, onClose, simulationData, chatHistory, onUpdateHistory, currentConversationId }) {
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatHistory, isOpen]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const message = input.trim();
    setInput('');
    
    if (!simulationData) {
      alert("Please run a simulation first so I have context!");
      return;
    }

    const newHistory = [...chatHistory, { role: 'user', content: message }];
    onUpdateHistory(newHistory);
    setIsLoading(true);

    try {
      const response = await axios.post(`${API_URL}/chat`, {
        message: message,
        history: newHistory,
        context: JSON.stringify(simulationData, null, 2),
        sim_id: currentConversationId
      });
      
      onUpdateHistory([...newHistory, { role: 'assistant', content: response.data.response }]);
    } catch (error) {
      onUpdateHistory([...newHistory, { role: 'assistant', content: "Sorry, I'm having trouble connecting. Please try again." }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <aside id="chatSidebar" className={`chat-sidebar ${isOpen ? 'active' : ''}`}>
      <div className="chat-sidebar-header">
        <div className="chat-sidebar-title">
          <Bot size={24} />
          <div>
            <h3>AI Assistant</h3>
            <p>Ask about simulation results</p>
          </div>
        </div>
        <button onClick={onClose} className="close-chat-btn">
          <X size={18} />
        </button>
      </div>

      <div className="chat-messages-container">
        <div className="chat-message bot">
          <div className="chat-avatar bot">
            <Bot size={16} />
          </div>
          <div className="chat-bubble bot">
            Hello! I'm ready to discuss the simulation results. Ask me anything about the analysis, graphs, or reports.
          </div>
        </div>
        
        {chatHistory.map((msg, idx) => (
          <div key={idx} className={`chat-message ${msg.role === 'assistant' ? 'bot' : 'user'}`}>
            <div className={`chat-avatar ${msg.role === 'assistant' ? 'bot' : 'user'}`}>
              {msg.role === 'assistant' ? <Bot size={16} /> : <User size={16} />}
            </div>
            <div className={`chat-bubble ${msg.role === 'assistant' ? 'bot' : 'user'}`}>
              {msg.content}
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="chat-message bot">
            <div className="chat-avatar bot">
              <Bot size={16} />
            </div>
            <div className="chat-bubble bot">
              <span style={{ opacity: 0.5 }}>Thinking...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-wrapper">
        <form className="chat-assistant-form" onSubmit={handleSubmit}>
          <input 
            type="text" 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a follow-up question..."
            autoComplete="off"
            disabled={isLoading}
          />
          <button type="submit" className="chat-send-btn" disabled={isLoading || !input.trim()}>
            <Send size={16} />
          </button>
        </form>
      </div>
    </aside>
  );
}
