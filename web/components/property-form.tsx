"use client";

import { useState } from "react";
import { X } from "lucide-react";

interface PropertyFormProps {
  property?: any;
  onSubmit: (data: any) => void;
  onCancel: () => void;
  isLoading: boolean;
}

export function PropertyForm({ property, onSubmit, onCancel, isLoading }: PropertyFormProps) {
  const [formData, setFormData] = useState({
    name: property?.name || "",
    address: property?.address || "",
    legal_description: property?.legal_description || "",
    aliases: property?.aliases?.join(", ") || "",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const aliases = formData.aliases
      .split(",")
      .map((a: string) => a.trim())
      .filter((a: string) => a);
    onSubmit({ ...formData, aliases });
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          {property ? "Edit Property" : "Add New Property"}
        </h3>
        <button
          onClick={onCancel}
          className="text-gray-400 hover:text-gray-600"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Property Name *
          </label>
          <input
            type="text"
            required
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            placeholder="e.g., 123 Main Street Development"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Address *
          </label>
          <input
            type="text"
            required
            value={formData.address}
            onChange={(e) => setFormData({ ...formData, address: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            placeholder="e.g., 123 Main St, Toronto, ON"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Legal Description
          </label>
          <input
            type="text"
            value={formData.legal_description}
            onChange={(e) => setFormData({ ...formData, legal_description: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            placeholder="e.g., Lot 1, Plan 123456"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Aliases
          </label>
          <input
            type="text"
            value={formData.aliases}
            onChange={(e) => setFormData({ ...formData, aliases: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            placeholder="Comma-separated aliases (e.g., Main Plaza, Block A)"
          />
          <p className="mt-1 text-xs text-gray-500">
            Alternative names or references for this property
          </p>
        </div>

        <div className="flex justify-end space-x-3 pt-4">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isLoading}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? "Saving..." : property ? "Update" : "Add"} Property
          </button>
        </div>
      </form>
    </div>
  );
}