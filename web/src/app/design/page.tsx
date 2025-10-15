// Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
import { DesignControl } from '@/components/DesignControl';

export default function DesignPage() {
  return (
    <div className="space-y-6">
      <div className="bg-card p-6 rounded-lg border border-border">
        <h1 className="text-2xl font-bold mb-2">Design Control</h1>
        <p className="text-muted-foreground">
          Create and manage PCB design projects. Start new designs, import existing files, and control the AI agent's design process.
        </p>
      </div>

      <DesignControl />
    </div>
  );
}
