import React from 'react';
import { Search, Plus, Building2 } from 'lucide-react';

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen }) => {
  const chatItems = [
    'New Chat'
  ];

  return (
    <div className={`${isOpen ? 'w-64' : 'w-0'} bg-gray-900 text-gray-100 flex flex-col transition-all duration-300 overflow-hidden border-r border-gray-700`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <button className="w-full flex items-center gap-3 bg-gray-800 hover:bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-sm font-medium transition-colors">
          <Plus size={16} />
          New Chat
        </button>

        {/* Menu Items */}
        <div className="mt-4 space-y-1">
          <div className="flex items-center gap-3 px-4 py-2 text-sm hover:bg-gray-800 rounded-lg cursor-pointer transition-colors">
            <Building2 size={16} />
            Workspace
          </div>
          <div className="flex items-center gap-3 px-4 py-2 text-sm hover:bg-gray-800 rounded-lg cursor-pointer transition-colors">
            <Search size={16} />
            Search
          </div>
        </div>
      </div>

      {/* Chat History */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-4">
          <div className="text-xs text-gray-500 uppercase font-medium tracking-wide mb-2">
            Today
          </div>
          <div className="space-y-1">
            {chatItems.map((item, index) => (
              <div
                key={index}
                className={`px-3 py-2 text-sm rounded-lg cursor-pointer transition-colors ${
                  index === 0 ? 'bg-gray-700 text-white' : 'text-gray-300 hover:bg-gray-800'
                }`}
              >
                {item}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;