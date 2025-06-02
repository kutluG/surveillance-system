import React, { useState } from 'react';
import { motion } from 'framer-motion';

export default function AlertsPage() {
  const [alerts] = useState([
    {
      id: 1,
      timestamp: '2025-06-02T14:32:00Z',
      type: 'Motion Detected',
      severity: 'medium',
      camera: 'Camera 03',
      location: 'Main Entrance',
      status: 'active',
      description: 'Unexpected movement detected in restricted area',
      aiConfidence: 0.92
    },
    {
      id: 2,
      timestamp: '2025-06-02T13:15:00Z',
      type: 'Unauthorized Access',
      severity: 'high',
      camera: 'Camera 07',
      location: 'Server Room',
      status: 'acknowledged',
      description: 'Person detected without proper authorization badge',
      aiConfidence: 0.98
    },
    {
      id: 3,
      timestamp: '2025-06-02T12:45:00Z',
      type: 'Object Recognition',
      severity: 'low',
      camera: 'Camera 01',
      location: 'Parking Lot',
      status: 'resolved',
      description: 'Unidentified vehicle detected',
      aiConfidence: 0.87
    },
    {
      id: 4,
      timestamp: '2025-06-02T11:20:00Z',
      type: 'Perimeter Breach',
      severity: 'high',
      camera: 'Camera 05',
      location: 'North Fence',
      status: 'active',
      description: 'Fence line compromised - possible intrusion attempt',
      aiConfidence: 0.95
    },
    {
      id: 5,
      timestamp: '2025-06-02T10:30:00Z',
      type: 'Loitering Detection',
      severity: 'medium',
      camera: 'Camera 02',
      location: 'Loading Dock',
      status: 'investigating',
      description: 'Person detected in area for extended period',
      aiConfidence: 0.89
    },
  ]);

  const [filterSeverity, setFilterSeverity] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');
  const [selectedAlert, setSelectedAlert] = useState(null);

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'high': return 'bg-red-500';
      case 'medium': return 'bg-yellow-500';
      case 'low': return 'bg-green-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return 'text-red-400 bg-red-500/20';
      case 'acknowledged': return 'text-yellow-400 bg-yellow-500/20';
      case 'investigating': return 'text-blue-400 bg-blue-500/20';
      case 'resolved': return 'text-green-400 bg-green-500/20';
      default: return 'text-gray-400 bg-gray-500/20';
    }
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const filteredAlerts = alerts.filter(alert => {
    const severityMatch = filterSeverity === 'all' || alert.severity === filterSeverity;
    const statusMatch = filterStatus === 'all' || alert.status === filterStatus;
    return severityMatch && statusMatch;
  });

  return (
    <div className="min-h-screen bg-slate-900 pt-20">
      <div className="container mx-auto px-6 py-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8"
        >
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Security Alerts</h1>
            <p className="text-slate-400">Monitor and manage security incidents</p>
          </div>
        </motion.div>

        {/* Alert Stats */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8"
        >
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-red-500/20 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <div>
                <p className="text-slate-400 text-sm">High Priority</p>
                <p className="text-xl font-bold text-white">{alerts.filter(a => a.severity === 'high').length}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-yellow-500/20 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <p className="text-slate-400 text-sm">Medium Priority</p>
                <p className="text-xl font-bold text-white">{alerts.filter(a => a.severity === 'medium').length}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-blue-500/20 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <p className="text-slate-400 text-sm">Active Alerts</p>
                <p className="text-xl font-bold text-white">{alerts.filter(a => a.status === 'active').length}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-green-500/20 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div>
                <p className="text-slate-400 text-sm">Resolved Today</p>
                <p className="text-xl font-bold text-white">{alerts.filter(a => a.status === 'resolved').length}</p>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Filters */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-slate-800 rounded-lg border border-slate-700 p-6 mb-8"
        >
          <div className="flex flex-wrap items-center gap-4">
            <div>
              <label className="text-slate-300 text-sm font-medium mb-2 block">Severity</label>
              <select
                value={filterSeverity}
                onChange={(e) => setFilterSeverity(e.target.value)}
                className="bg-slate-700 border border-slate-600 text-white rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Severities</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
            
            <div>
              <label className="text-slate-300 text-sm font-medium mb-2 block">Status</label>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="bg-slate-700 border border-slate-600 text-white rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Statuses</option>
                <option value="active">Active</option>
                <option value="acknowledged">Acknowledged</option>
                <option value="investigating">Investigating</option>
                <option value="resolved">Resolved</option>
              </select>
            </div>
            
            <div className="ml-auto">
              <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                Export Alerts
              </button>
            </div>
          </div>
        </motion.div>

        {/* Alerts List */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="space-y-4"
        >
          {filteredAlerts.map((alert, index) => (
            <motion.div
              key={alert.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className="bg-slate-800 rounded-lg border border-slate-700 p-6 hover:border-blue-500/50 transition-colors cursor-pointer"
              onClick={() => setSelectedAlert(alert)}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-4">
                  <div className={`w-4 h-4 ${getSeverityColor(alert.severity)} rounded-full mt-1`}></div>
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <h3 className="text-lg font-semibold text-white">{alert.type}</h3>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(alert.status)}`}>
                        {alert.status.charAt(0).toUpperCase() + alert.status.slice(1)}
                      </span>
                    </div>
                    <p className="text-slate-300 mb-2">{alert.description}</p>
                    <div className="flex items-center space-x-6 text-sm text-slate-400">
                      <span>{alert.camera} • {alert.location}</span>
                      <span>AI Confidence: {(alert.aiConfidence * 100).toFixed(0)}%</span>
                      <span>{formatTimestamp(alert.timestamp)}</span>
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center space-x-2">
                  <button className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors">
                    Investigate
                  </button>
                  <button className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700 transition-colors">
                    Resolve
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>

        {/* Alert Detail Modal */}
        {selectedAlert && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={() => setSelectedAlert(null)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="bg-slate-800 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-6">
                <div className="flex justify-between items-start mb-6">
                  <div>
                    <h2 className="text-2xl font-bold text-white mb-2">{selectedAlert.type}</h2>
                    <div className="flex items-center space-x-3">
                      <div className={`w-3 h-3 ${getSeverityColor(selectedAlert.severity)} rounded-full`}></div>
                      <span className="text-slate-300 capitalize">{selectedAlert.severity} Priority</span>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(selectedAlert.status)}`}>
                        {selectedAlert.status.charAt(0).toUpperCase() + selectedAlert.status.slice(1)}
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={() => setSelectedAlert(null)}
                    className="text-slate-400 hover:text-white"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
                
                <div className="grid grid-cols-2 gap-6 mb-6">
                  <div>
                    <p className="text-slate-400 text-sm mb-1">Camera</p>
                    <p className="text-white">{selectedAlert.camera}</p>
                  </div>
                  <div>
                    <p className="text-slate-400 text-sm mb-1">Location</p>
                    <p className="text-white">{selectedAlert.location}</p>
                  </div>
                  <div>
                    <p className="text-slate-400 text-sm mb-1">Timestamp</p>
                    <p className="text-white">{formatTimestamp(selectedAlert.timestamp)}</p>
                  </div>
                  <div>
                    <p className="text-slate-400 text-sm mb-1">AI Confidence</p>
                    <p className="text-white">{(selectedAlert.aiConfidence * 100).toFixed(1)}%</p>
                  </div>
                </div>
                
                <div className="mb-6">
                  <p className="text-slate-400 text-sm mb-2">Description</p>
                  <p className="text-white">{selectedAlert.description}</p>
                </div>
                
                <div className="aspect-video bg-slate-700 rounded-lg mb-6 flex items-center justify-center">
                  <div className="text-center">
                    <svg className="w-16 h-16 text-slate-500 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    <p className="text-slate-400 text-sm">Alert footage would appear here</p>
                  </div>
                </div>
                
                <div className="flex space-x-3">
                  <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                    Acknowledge
                  </button>
                  <button className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors">
                    Investigate
                  </button>
                  <button className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors">
                    Resolve
                  </button>
                  <button className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors">
                    Download Evidence
                  </button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
