"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import { 
  Calendar, 
  MapPin, 
  FileText, 
  MessageSquare, 
  CheckCircle, 
  XCircle,
  AlertCircle,
  ChevronDown,
  ChevronUp
} from "lucide-react";

interface AlertCardProps {
  alert: any;
}

export function AlertCard({ alert }: AlertCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [comment, setComment] = useState("");
  const queryClient = useQueryClient();

  const statusColors = {
    pending: "bg-yellow-100 text-yellow-800",
    reviewing: "bg-blue-100 text-blue-800",
    resolved: "bg-green-100 text-green-800",
    false_positive: "bg-gray-100 text-gray-800",
  };

  const statusIcons = {
    pending: AlertCircle,
    reviewing: AlertCircle,
    resolved: CheckCircle,
    false_positive: XCircle,
  };

  const StatusIcon = statusIcons[alert.review_status as keyof typeof statusIcons];

  const updateStatus = useMutation({
    mutationFn: (status: string) => 
      apiClient.alerts.updateStatus(alert.id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
    },
  });

  const addComment = useMutation({
    mutationFn: () => apiClient.alerts.addComment(alert.id, comment),
    onSuccess: () => {
      setComment("");
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
    },
  });

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm">
      <div className="p-6">
        <div className="flex justify-between items-start">
          <div className="flex-1">
            <div className="flex items-center space-x-2 mb-2">
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[alert.review_status as keyof typeof statusColors]}`}>
                <StatusIcon className="w-3 h-3 inline mr-1" />
                {alert.review_status.replace("_", " ").toUpperCase()}
              </span>
              <span className="text-sm text-gray-500">
                Relevance: {(alert.relevance_score * 100).toFixed(0)}%
              </span>
            </div>
            
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              {alert.title}
            </h3>
            
            <div className="flex items-center space-x-4 text-sm text-gray-600">
              <span className="flex items-center">
                <Calendar className="w-4 h-4 mr-1" />
                {new Date(alert.meeting_date).toLocaleDateString()}
              </span>
              <span className="flex items-center">
                <MapPin className="w-4 h-4 mr-1" />
                {alert.municipality}
              </span>
              <span className="flex items-center">
                <FileText className="w-4 h-4 mr-1" />
                {alert.meeting_type}
              </span>
              {alert.comment_count > 0 && (
                <span className="flex items-center">
                  <MessageSquare className="w-4 h-4 mr-1" />
                  {alert.comment_count} comments
                </span>
              )}
            </div>

            {alert.property_matches.length > 0 && (
              <div className="mt-3">
                <span className="text-sm font-medium text-gray-700">Properties: </span>
                <span className="text-sm text-gray-600">
                  {alert.property_matches.join(", ")}
                </span>
              </div>
            )}

            {alert.rule_matches.length > 0 && (
              <div className="mt-2">
                <span className="text-sm font-medium text-gray-700">Matched Rules: </span>
                <span className="text-sm text-gray-600">
                  {alert.rule_matches.join(", ")}
                </span>
              </div>
            )}
          </div>

          <button
            onClick={() => setExpanded(!expanded)}
            className="ml-4 text-gray-400 hover:text-gray-600"
          >
            {expanded ? <ChevronUp /> : <ChevronDown />}
          </button>
        </div>

        {expanded && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="flex space-x-2 mb-4">
              <button
                onClick={() => updateStatus.mutate("reviewing")}
                className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm"
                disabled={alert.review_status === "reviewing"}
              >
                Mark as Reviewing
              </button>
              <button
                onClick={() => updateStatus.mutate("resolved")}
                className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 text-sm"
                disabled={alert.review_status === "resolved"}
              >
                Mark as Resolved
              </button>
              <button
                onClick={() => updateStatus.mutate("false_positive")}
                className="px-3 py-1 bg-gray-600 text-white rounded hover:bg-gray-700 text-sm"
                disabled={alert.review_status === "false_positive"}
              >
                False Positive
              </button>
              <a
                href={alert.url}
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-1 bg-indigo-600 text-white rounded hover:bg-indigo-700 text-sm"
              >
                View Document
              </a>
            </div>

            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Add Comment
              </label>
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Enter your comment..."
                />
                <button
                  onClick={() => addComment.mutate()}
                  disabled={!comment.trim()}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Add
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}