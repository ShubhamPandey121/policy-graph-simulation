import React, { useState, useEffect } from 'react';
import { Menu, X, Sparkles, MessageCircle } from 'lucide-react';
import Sidebar from './components/Sidebar';
import WelcomeScreen from './components/WelcomeScreen';
import ResultsScreen from './components/ResultsScreen';
import InputArea from './components/InputArea';
import ChatAssistant from './components/ChatAssistant';
import axios from 'axios';

const API_URL = 'http://localhost:8000';

function App() {
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'dark');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [chatSidebarOpen, setChatSidebarOpen] = useState(false);
  
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  
  const [isLoading, setIsLoading] = useState(false);
  
  useEffect(() => {
    // Apply theme
    document.documentElement.classList.toggle('dark', theme === 'dark');
    localStorage.setItem('theme', theme);
  }, [theme]);
  
  useEffect(() => {
    // Fetch conversations from MongoDB backend
    const fetchSimulations = async () => {
      try {
        const res = await axios.get(`${API_URL}/simulations`);
        if (res.data && res.data.simulations) {
          // Map MongoDB _id to id for the frontend
          const sims = res.data.simulations.map(sim => ({
            ...sim,
            id: sim._id
          }));
          setConversations(sims);
        }
      } catch (e) {
        console.error('Failed to fetch simulations from DB', e);
      }
    };
    fetchSimulations();
  }, []);
  
  const saveConversations = (newConversations) => {
    setConversations(newConversations);
    // No longer using localStorage, backend persists it!
  };

  const handleNewSimulation = () => {
    setCurrentConversationId(null);
    setChatSidebarOpen(false);
    setSidebarOpen(false);
  };
  
  const selectConversation = (id) => {
    setCurrentConversationId(id);
    setSidebarOpen(false);
  };
  
  const deleteConversation = (id, event) => {
    event.stopPropagation();
    const newConvs = conversations.filter(c => c.id !== id);
    saveConversations(newConvs);
    if (currentConversationId === id) {
      handleNewSimulation();
    }
  };

  const handleSubmit = async (query, files) => {
    if (!query && files.length === 0) return;
    
    setIsLoading(true);
    const formData = new FormData();
    if (query) formData.append('query', query);
    
    files.forEach(file => {
      if (file.type === 'application/pdf') {
        formData.append('pdf', file);
      } else if (file.type.startsWith('image/')) {
        formData.append('image', file);
      }
    });

    try {
      const response = await axios.post(`${API_URL}/analyze`, formData);
      const data = response.data;
      
      let newConvs = [...conversations];
      let currentConv = newConvs.find(c => c.id === currentConversationId);
      
      if (!currentConv) {
        currentConv = {
          id: data._id || Date.now().toString(), // Use Mongo _id if returned
          title: query ? query.slice(0, 60) + (query.length > 60 ? '...' : '') : 'Document Analysis',
          simulationData: data,
          chatHistory: [],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        };
        newConvs.unshift(currentConv);
        setCurrentConversationId(currentConv.id);
      } else {
        currentConv.simulationData = data;
        currentConv.updatedAt = new Date().toISOString();
      }
      
      saveConversations(newConvs);
      setChatSidebarOpen(true);
    } catch (error) {
      alert('Simulation Error: ' + (error.response?.data?.detail || error.message));
    } finally {
      setIsLoading(false);
    }
  };

  const updateChatHistory = (history) => {
    let newConvs = [...conversations];
    let currentConv = newConvs.find(c => c.id === currentConversationId);
    if (currentConv) {
      currentConv.chatHistory = history;
      currentConv.updatedAt = new Date().toISOString();
      saveConversations(newConvs);
    }
  };

  const currentSimulationData = conversations.find(c => c.id === currentConversationId)?.simulationData;
  const chatHistory = conversations.find(c => c.id === currentConversationId)?.chatHistory || [];

  return (
    <>
      <div className="animated-bg">
        <div className="bg-blob bg-blob-1"></div>
        <div className="bg-blob bg-blob-2"></div>
      </div>

      <button onClick={() => setSidebarOpen(!sidebarOpen)} className="hamburger-btn" aria-label="Toggle menu">
        {sidebarOpen ? <X className="icon" /> : <Menu className="icon" />}
      </button>

      <div 
        className={`sidebar-backdrop ${sidebarOpen ? 'active' : ''}`} 
        onClick={() => setSidebarOpen(false)}
      ></div>

      <Sidebar 
        theme={theme}
        setTheme={setTheme}
        isOpen={sidebarOpen}
        conversations={conversations}
        currentConversationId={currentConversationId}
        onNewChat={handleNewSimulation}
        onSelectConversation={selectConversation}
        onDeleteConversation={deleteConversation}
      />

      <main className={`main-content ${chatSidebarOpen ? 'chat-open' : ''}`}>
        {!currentSimulationData ? (
          <WelcomeScreen onSubmit={(query) => handleSubmit(query, [])} />
        ) : (
          <ResultsScreen 
            data={currentSimulationData} 
            onNewSimulation={handleNewSimulation} 
          />
        )}
        
        <InputArea onSubmit={handleSubmit} isLoading={isLoading} />
      </main>

      {!chatSidebarOpen && currentSimulationData && (
        <button className="floating-chat-btn" onClick={() => setChatSidebarOpen(true)}>
          <MessageCircle />
        </button>
      )}

      <ChatAssistant 
        isOpen={chatSidebarOpen}
        onClose={() => setChatSidebarOpen(false)}
        simulationData={currentSimulationData}
        chatHistory={chatHistory}
        onUpdateHistory={updateChatHistory}
        currentConversationId={currentConversationId}
      />

      {isLoading && (
        <div className="loading-overlay">
          <div className="loading-content">
            <div className="loading-spinner"></div>
            <p className="loading-text">Analyzing policy impacts...</p>
            <p className="loading-subtext">Running multi-agent simulation</p>
          </div>
        </div>
      )}
    </>
  );
}

export default App;
