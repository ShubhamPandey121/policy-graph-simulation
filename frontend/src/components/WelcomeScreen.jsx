import React from 'react';
import { Sparkles, GraduationCap, Heart, TrendingUp, Leaf, Users, Building2, Scale, Zap } from 'lucide-react';

export default function WelcomeScreen({ onSubmit }) {
  const handleExampleClick = (prompt) => {
    onSubmit(prompt);
  };

  return (
    <div className="welcome-screen">
      <div className="welcome-content">
        <div className="welcome-logo">
          <div className="logo-glow"></div>
          <Sparkles className="logo-icon" />
        </div>

        <h1 className="welcome-title">Policy Impact Simulator</h1>
        <p className="welcome-subtitle">
          Analyze policies using AI-powered causal modeling to predict secondary and long-term impacts before implementation
        </p>

        <div className="example-prompts">
          <div className="example-card" onClick={() => handleExampleClick("Analyze the impact of free higher education on employment rates")}>
            <span className="example-icon">🎓</span>
            <div>
              <h3>Education Policy</h3>
              <p>Analyze the impact of free higher education on employment rates</p>
            </div>
          </div>
          <div className="example-card" onClick={() => handleExampleClick("Simulate universal healthcare implementation effects")}>
            <span className="example-icon">🏥</span>
            <div>
              <h3>Healthcare Reform</h3>
              <p>Simulate universal healthcare implementation effects</p>
            </div>
          </div>
          <div className="example-card" onClick={() => handleExampleClick("Predict outcomes of minimum wage increase")}>
            <span className="example-icon">💰</span>
            <div>
              <h3>Economic Policy</h3>
              <p>Predict outcomes of minimum wage increase</p>
            </div>
          </div>
          <div className="example-card" onClick={() => handleExampleClick("Model carbon tax impact on industries")}>
            <span className="example-icon">🌱</span>
            <div>
              <h3>Environmental</h3>
              <p>Model carbon tax impact on industries</p>
            </div>
          </div>
        </div>
      </div>

      <div className="policy-grid-section">
        <div className="policy-grid-header">
          <h2>Explore Policy Categories</h2>
          <p>Select a category to get started with AI-powered analysis</p>
        </div>
        <div className="policy-grid">
          {[
            { icon: GraduationCap, title: 'Education', desc: 'Analyze educational reforms and their long-term societal impact' },
            { icon: Heart, title: 'Healthcare', desc: 'Model healthcare policy effects on population health outcomes' },
            { icon: TrendingUp, title: 'Economic', desc: 'Predict economic policy impacts on growth and employment' },
            { icon: Leaf, title: 'Environmental', desc: 'Simulate environmental regulations and sustainability effects' },
            { icon: Users, title: 'Social', desc: 'Evaluate social programs and community welfare initiatives' },
            { icon: Building2, title: 'Infrastructure', desc: 'Assess infrastructure investments and urban development' },
            { icon: Scale, title: 'Legal', desc: 'Analyze regulatory changes and legal framework updates' },
            { icon: Zap, title: 'Technology', desc: 'Evaluate tech policy impacts on innovation and privacy' }
          ].map((cat, i) => (
            <div className="policy-card" key={i}>
              <div className="policy-icon-wrapper">
                <cat.icon size={24} />
              </div>
              <h3>{cat.title}</h3>
              <p>{cat.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
