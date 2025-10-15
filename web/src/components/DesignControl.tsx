// Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
'use client';

import { useState } from 'react';
import { useDesigns, useAgentStatus } from '@/hooks/useApi';

export function DesignControl() {
  const { designs, loading, error, createDesign, deleteDesign } = useDesigns();
  const { status: agentStatus, startAgent, stopAgent } = useAgentStatus();
  const [isCreating, setIsCreating] = useState(false);
  const [newDesign, setNewDesign] = useState({
    name: '',
    description: '',
    requirements: ''
  });

  const handleCreateDesign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDesign.name.trim()) return;

    try {
      setIsCreating(true);
      await createDesign({
        name: newDesign.name,
        description: newDesign.description,
        requirements: { description: newDesign.requirements }
      });
      
      // Reset form
      setNewDesign({ name: '', description: '', requirements: '' });
      alert('Design created successfully!');
    } catch (err) {
      alert('Error creating design: ' + (err instanceof Error ? err.message : 'Unknown error'));
    } finally {
      setIsCreating(false);
    }
  };

  const handleStartAgent = async (designId: string) => {
    try {
      await startAgent(designId);
      alert('Agent started successfully!');
    } catch (err) {
      alert('Error starting agent: ' + (err instanceof Error ? err.message : 'Unknown error'));
    }
  };

  const handleStopAgent = async () => {
    try {
      await stopAgent();
      alert('Agent stopped successfully!');
    } catch (err) {
      alert('Error stopping agent: ' + (err instanceof Error ? err.message : 'Unknown error'));
    }
  };

  const handleDeleteDesign = async (id: string, name: string) => {
    if (confirm(`Are you sure you want to delete "${name}"?`)) {
      try {
        await deleteDesign(id);
        alert('Design deleted successfully!');
      } catch (err) {
        alert('Error deleting design: ' + (err instanceof Error ? err.message : 'Unknown error'));
      }
    }
  };

  if (loading) {
    return (
      <div className="p-6 text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
        <p className="mt-2 text-muted-foreground">Loading designs...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Agent Status */}
      <div className="bg-card p-4 rounded-lg border border-border">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-medium">Agent Status</h3>
            <p className="text-sm text-muted-foreground">
              Status: {agentStatus?.agent_status || 'unknown'}
            </p>
            {agentStatus?.current_task && (
              <p className="text-sm text-muted-foreground">
                Current task: {agentStatus.current_task}
              </p>
            )}
          </div>
          <div className="space-x-2">
            <button
              onClick={handleStopAgent}
              className="px-3 py-1 bg-red-500 text-white text-sm rounded hover:bg-red-600"
            >
              Stop Agent
            </button>
          </div>
        </div>
      </div>

      {/* Create New Design */}
      <div className="bg-card p-6 rounded-lg border border-border">
        <h2 className="text-lg font-semibold mb-4">Create New Design</h2>
        <form onSubmit={handleCreateDesign} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Project Name</label>
            <input
              type="text"
              value={newDesign.name}
              onChange={(e) => setNewDesign({ ...newDesign, name: e.target.value })}
              placeholder="Enter project name..."
              className="w-full px-3 py-2 border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Description</label>
            <textarea
              value={newDesign.description}
              onChange={(e) => setNewDesign({ ...newDesign, description: e.target.value })}
              placeholder="Describe your PCB project..."
              rows={3}
              className="w-full px-3 py-2 border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Requirements</label>
            <textarea
              value={newDesign.requirements}
              onChange={(e) => setNewDesign({ ...newDesign, requirements: e.target.value })}
              placeholder="Specify technical requirements, components needed, constraints..."
              rows={4}
              className="w-full px-3 py-2 border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <button
            type="submit"
            disabled={isCreating || !newDesign.name.trim()}
            className="bg-primary text-primary-foreground px-6 py-2 rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isCreating ? 'Creating...' : 'Create Design'}
          </button>
        </form>
      </div>

      {/* Design List */}
      <div className="bg-card p-6 rounded-lg border border-border">
        <h2 className="text-lg font-semibold mb-4">Your Designs ({designs.length})</h2>
        
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg mb-4">
            <p className="text-red-700 text-sm">Error: {error}</p>
          </div>
        )}

        <div className="space-y-4">
          {designs.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">
              No designs yet. Create your first PCB design above!
            </p>
          ) : (
            designs.map((design: any) => (
              <div key={design.id} className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
                <div className="flex items-center space-x-4">
                  <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center">
                    <svg className="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="font-medium">{design.name}</h3>
                    <p className="text-sm text-muted-foreground">{design.description || 'No description'}</p>
                    <div className="flex items-center space-x-2 mt-1">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                        design.status === 'completed' ? 'bg-green-100 text-green-600' :
                        design.status === 'in-progress' ? 'bg-yellow-100 text-yellow-600' :
                        design.status === 'failed' ? 'bg-red-100 text-red-600' :
                        'bg-gray-100 text-gray-600'
                      }`}>
                        {design.status || 'draft'}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        Created: {new Date(design.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleStartAgent(design.id)}
                    className="p-2 text-green-600 hover:bg-green-50 rounded-md transition-colors"
                    title="Start agent for this design"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1.586a1 1 0 01.707.293l2.414 2.414a1 1 0 00.707.293H15M9 10v4a6 6 0 006 6v-4a6 6 0 00-6-6M9 10V7a3 3 0 013-3h2.25" />
                    </svg>
                  </button>
                  <button
                    onClick={() => handleDeleteDesign(design.id, design.name)}
                    className="p-2 text-red-600 hover:bg-red-50 rounded-md transition-colors"
                    title="Delete design"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}