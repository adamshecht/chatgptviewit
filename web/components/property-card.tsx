"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import { Building, MapPin, FileText, Edit, Trash2, Power } from "lucide-react";
import { PropertyForm } from "./property-form";

interface PropertyCardProps {
  property: any;
  isAdmin: boolean;
}

export function PropertyCard({ property, isAdmin }: PropertyCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const queryClient = useQueryClient();

  const updateProperty = useMutation({
    mutationFn: (data: any) => apiClient.properties.update(property.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["properties"] });
      setIsEditing(false);
    },
  });

  const deleteProperty = useMutation({
    mutationFn: () => apiClient.properties.delete(property.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["properties"] });
    },
  });



  if (isEditing) {
    return (
      <PropertyForm
        property={property}
        onSubmit={(data) => updateProperty.mutate(data)}
        onCancel={() => setIsEditing(false)}
        isLoading={updateProperty.isPending}
      />
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center">
          <Building className="w-5 h-5 text-gray-400 mr-2" />
          <h3 className="text-lg font-semibold text-gray-900">{property.address}</h3>
        </div>
        <div className="flex items-center space-x-2">
          {property.property_type && (
            <span className="px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
              {property.property_type}
            </span>
          )}
          {property.zoning && (
            <span className="px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
              {property.zoning}
            </span>
          )}
        </div>
      </div>

      <div className="space-y-2 text-sm text-gray-600">
        <div className="flex items-start">
          <MapPin className="w-4 h-4 text-gray-400 mr-2 mt-0.5" />
          <span>
            {property.city && property.province 
              ? `${property.city}, ${property.province}` 
              : property.city || property.province || 'Location not specified'}
            {property.postal_code && ` ${property.postal_code}`}
          </span>
        </div>
        {property.size_sqft && (
          <div className="flex items-start">
            <FileText className="w-4 h-4 text-gray-400 mr-2 mt-0.5" />
            <span>{property.size_sqft.toLocaleString()} sq ft</span>
          </div>
        )}
        {property.year_built && (
          <div className="flex items-start">
            <Building className="w-4 h-4 text-gray-400 mr-2 mt-0.5" />
            <span>Built in {property.year_built}</span>
          </div>
        )}
        {property.notes && (
          <div className="mt-2 p-2 bg-gray-50 rounded text-xs">
            {property.notes}
          </div>
        )}
      </div>

      {isAdmin && (
        <div className="mt-4 pt-4 border-t border-gray-200 flex justify-between">
          <div className="flex space-x-2">
            <button
              onClick={() => setIsEditing(true)}
              className="p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded"
              title="Edit"
            >
              <Edit className="w-4 h-4" />
            </button>

            <button
              onClick={() => {
                if (confirm("Are you sure you want to delete this property?")) {
                  deleteProperty.mutate();
                }
              }}
              className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded"
              title="Delete"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}