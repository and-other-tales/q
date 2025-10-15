// Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
export default function Configuration() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-card p-6 rounded-lg border border-border">
        <h1 className="text-2xl font-bold mb-2">Configuration</h1>
        <p className="text-muted-foreground">
          Configure the PCB design agent settings, preferences, and integrations to optimize your design workflow.
        </p>
      </div>

      {/* Agent Settings */}
      <div className="bg-card p-6 rounded-lg border border-border">
        <h2 className="text-lg font-semibold mb-4">Agent Settings</h2>
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Model Temperature</label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                defaultValue="0.7"
                className="w-full"
              />
              <div className="flex justify-between text-xs text-muted-foreground mt-1">
                <span>Conservative (0.0)</span>
                <span>Balanced (0.7)</span>
                <span>Creative (1.0)</span>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Max Tokens</label>
              <input
                type="number"
                defaultValue="4000"
                className="w-full px-3 py-2 border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">AI Model</label>
            <select className="w-full px-3 py-2 border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary">
              <option>gpt-4-turbo</option>
              <option>gpt-4</option>
              <option>claude-3-opus</option>
              <option>claude-3-sonnet</option>
            </select>
          </div>
        </div>
      </div>

      {/* Component Database */}
      <div className="bg-card p-6 rounded-lg border border-border">
        <h2 className="text-lg font-semibold mb-4">Component Database</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Preferred Suppliers</label>
            <div className="space-y-2">
              {['Digi-Key', 'Mouser', 'LCSC', 'Arrow'].map((supplier) => (
                <label key={supplier} className="flex items-center space-x-2">
                  <input type="checkbox" defaultChecked className="rounded border-border" />
                  <span className="text-sm">{supplier}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Search Timeout (seconds)</label>
              <input
                type="number"
                defaultValue="30"
                className="w-full px-3 py-2 border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Max Results per Search</label>
              <input
                type="number"
                defaultValue="50"
                className="w-full px-3 py-2 border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Design Rules */}
      <div className="bg-card p-6 rounded-lg border border-border">
        <h2 className="text-lg font-semibold mb-4">Design Rules</h2>
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Min Trace Width (mm)</label>
              <input
                type="number"
                step="0.01"
                defaultValue="0.1"
                className="w-full px-3 py-2 border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Min Via Size (mm)</label>
              <input
                type="number"
                step="0.01"
                defaultValue="0.2"
                className="w-full px-3 py-2 border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Min Clearance (mm)</label>
              <input
                type="number"
                step="0.01"
                defaultValue="0.15"
                className="w-full px-3 py-2 border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Manufacturing Process</label>
            <select className="w-full px-3 py-2 border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary">
              <option>Standard PCB</option>
              <option>HDI (High Density Interconnect)</option>
              <option>Flex PCB</option>
              <option>Rigid-Flex</option>
            </select>
          </div>
        </div>
      </div>

      {/* Integrations */}
      <div className="bg-card p-6 rounded-lg border border-border">
        <h2 className="text-lg font-semibold mb-4">Integrations</h2>
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div>
                <h3 className="font-medium">KiCad Integration</h3>
                <p className="text-sm text-muted-foreground">Connect to KiCad for direct file manipulation</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span className="px-2 py-1 bg-green-500/10 text-green-600 text-xs font-medium rounded-full">Connected</span>
              <button className="px-3 py-1 text-xs bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/90">
                Configure
              </button>
            </div>
          </div>

          <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-orange-500/10 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              </div>
              <div>
                <h3 className="font-medium">SPICE Simulation</h3>
                <p className="text-sm text-muted-foreground">Enable circuit simulation and analysis</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span className="px-2 py-1 bg-yellow-500/10 text-yellow-600 text-xs font-medium rounded-full">Pending</span>
              <button className="px-3 py-1 text-xs bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/90">
                Setup
              </button>
            </div>
          </div>

          <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-purple-500/10 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
                </svg>
              </div>
              <div>
                <h3 className="font-medium">Cloud Storage</h3>
                <p className="text-sm text-muted-foreground">Sync designs to cloud storage</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span className="px-2 py-1 bg-red-500/10 text-red-600 text-xs font-medium rounded-full">Disconnected</span>
              <button className="px-3 py-1 text-xs bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/90">
                Connect
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Save Settings */}
      <div className="flex justify-end space-x-4">
        <button className="px-6 py-2 text-secondary-foreground bg-secondary rounded-md hover:bg-secondary/90 transition-colors">
          Reset to Defaults
        </button>
        <button className="px-6 py-2 text-primary-foreground bg-primary rounded-md hover:bg-primary/90 transition-colors">
          Save Changes
        </button>
      </div>
    </div>
  );
}