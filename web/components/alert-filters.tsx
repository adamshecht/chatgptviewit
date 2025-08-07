"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api";

interface AlertFiltersProps {
  filters: any;
  onFiltersChange: (filters: any) => void;
}

export function AlertFilters({ filters, onFiltersChange }: AlertFiltersProps) {
  const { data: properties } = useQuery({
    queryKey: ["properties"],
    queryFn: () => apiClient.properties.list(),
  });

  const { data: municipalities } = useQuery({
    queryKey: ["municipalities"],
    queryFn: () => apiClient.companies.getMunicipalities(),
  });

  return (
    <div className="bg-white p-4 rounded-lg border border-gray-200">
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Status
          </label>
          <select
            value={filters.status || ""}
            onChange={(e) => 
              onFiltersChange({ ...filters, status: e.target.value || null })
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="reviewing">Reviewing</option>
            <option value="resolved">Resolved</option>
            <option value="false_positive">False Positive</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Municipality
          </label>
          <select
            value={filters.municipality || ""}
            onChange={(e) => 
              onFiltersChange({ ...filters, municipality: e.target.value || null })
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">All Municipalities</option>
            {municipalities?.map((muni: string) => (
              <option key={muni} value={muni}>
                {muni}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Property
          </label>
          <select
            value={filters.property_id || ""}
            onChange={(e) => 
              onFiltersChange({ ...filters, property_id: e.target.value || null })
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">All Properties</option>
            {properties?.map((prop: any) => (
              <option key={prop.id} value={prop.id}>
                {prop.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Start Date
          </label>
          <input
            type="date"
            value={filters.start_date || ""}
            onChange={(e) => 
              onFiltersChange({ ...filters, start_date: e.target.value || null })
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            End Date
          </label>
          <input
            type="date"
            value={filters.end_date || ""}
            onChange={(e) => 
              onFiltersChange({ ...filters, end_date: e.target.value || null })
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
      </div>

      <div className="mt-4 flex justify-end">
        <button
          onClick={() => 
            onFiltersChange({
              status: null,
              municipality: null,
              property_id: null,
              start_date: null,
              end_date: null,
            })
          }
          className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
        >
          Clear Filters
        </button>
      </div>
    </div>
  );
}