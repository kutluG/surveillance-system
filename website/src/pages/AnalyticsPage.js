import React, { useState } from 'react';
import { motion } from 'framer-motion';

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState('7d');
  
  // Mock data for charts
  const alertTrends = {
    '7d': [2, 5, 3, 8, 4, 6, 3],
    '30d': [15, 23, 18, 32, 28, 21, 35, 29, 24, 31, 27, 19, 22, 26, 33, 25, 20, 28, 31, 24, 27, 30, 26, 23, 29, 32, 28, 25, 31, 27],
    '90d': Array.from({length: 90}, () => Math.floor(Math.random() * 40) + 10)
  };

  const securityMetrics = {
    threatsDetected: 47,
    falsePositives: 3,
    avgResponseTime: '2.3 min',
    systemUptime: '99.97%'
  };

  const topCameras = [
    { name: 'Main Entrance', alerts: 23, uptime: 99.9 },
    { name: 'Parking Lot A', alerts: 18, uptime: 100 },
    { name: 'Loading Dock', alerts: 15, uptime: 98.7 },
    { name: 'Office Corridor', alerts: 12, uptime: 99.8 }
  ];

  const alertTypes = [
    { type: 'Motion Detection', count: 18, percentage: 38 },
    { type: 'Unauthorized Access', count: 14, percentage: 30 },
    { type: 'Object Recognition', count: 9, percentage: 19 },
    { type: 'Perimeter Breach', count: 6, percentage: 13 }
  ];

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
            <h1 className="text-3xl font-bold text-white mb-2">Security Analytics</h1>
            <p className="text-slate-400">Insights and trends from your surveillance system</p>
          </div>
          
          <div className="flex items-center space-x-4 mt-4 md:mt-0">
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              className="bg-slate-800 border border-slate-700 text-white rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
            >
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
              <option value="90d">Last 90 days</option>
            </select>
            
            <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
              Export Report
            </button>
          </div>
        </motion.div>

        {/* Key Metrics */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8"
        >
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">Threats Detected</p>
                <p className="text-2xl font-bold text-white">{securityMetrics.threatsDetected}</p>
                <p className="text-green-400 text-sm">↑ 12% from last period</p>
              </div>
              <div className="w-12 h-12 bg-red-500/20 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">False Positives</p>
                <p className="text-2xl font-bold text-white">{securityMetrics.falsePositives}</p>
                <p className="text-red-400 text-sm">↓ 25% from last period</p>
              </div>
              <div className="w-12 h-12 bg-yellow-500/20 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">Avg Response Time</p>
                <p className="text-2xl font-bold text-white">{securityMetrics.avgResponseTime}</p>
                <p className="text-green-400 text-sm">↓ 8% from last period</p>
              </div>
              <div className="w-12 h-12 bg-blue-500/20 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">System Uptime</p>
                <p className="text-2xl font-bold text-white">{securityMetrics.systemUptime}</p>
                <p className="text-green-400 text-sm">↑ 0.1% from last period</p>
              </div>
              <div className="w-12 h-12 bg-green-500/20 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
          </div>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* Alert Trends Chart */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-slate-800 rounded-lg border border-slate-700"
          >
            <div className="p-6 border-b border-slate-700">
              <h3 className="text-lg font-semibold text-white">Alert Trends</h3>
              <p className="text-slate-400 text-sm">Daily alert count over time</p>
            </div>
            <div className="p-6">
              <div className="h-64 flex items-end justify-between space-x-2">
                {alertTrends[timeRange].slice(0, 7).map((count, index) => (
                  <div key={index} className="flex-1 flex flex-col items-center">
                    <div 
                      className="w-full bg-blue-500 rounded-t transition-all duration-500"
                      style={{ height: `${(count / Math.max(...alertTrends[timeRange].slice(0, 7))) * 200}px` }}
                    ></div>
                    <span className="text-slate-400 text-xs mt-2">Day {index + 1}</span>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>

          {/* Alert Types Distribution */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-slate-800 rounded-lg border border-slate-700"
          >
            <div className="p-6 border-b border-slate-700">
              <h3 className="text-lg font-semibold text-white">Alert Types</h3>
              <p className="text-slate-400 text-sm">Distribution of alert categories</p>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                {alertTypes.map((alert, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className={`w-3 h-3 rounded-full ${
                        index === 0 ? 'bg-blue-500' :
                        index === 1 ? 'bg-red-500' :
                        index === 2 ? 'bg-yellow-500' : 'bg-green-500'
                      }`}></div>
                      <span className="text-slate-300">{alert.type}</span>
                    </div>
                    <div className="flex items-center space-x-3">
                      <span className="text-white font-medium">{alert.count}</span>
                      <div className="w-20 h-2 bg-slate-700 rounded-full overflow-hidden">
                        <div 
                          className={`h-full ${
                            index === 0 ? 'bg-blue-500' :
                            index === 1 ? 'bg-red-500' :
                            index === 2 ? 'bg-yellow-500' : 'bg-green-500'
                          }`}
                          style={{ width: `${alert.percentage}%` }}
                        ></div>
                      </div>
                      <span className="text-slate-400 text-sm w-10">{alert.percentage}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Top Performing Cameras */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="bg-slate-800 rounded-lg border border-slate-700"
          >
            <div className="p-6 border-b border-slate-700">
              <h3 className="text-lg font-semibold text-white">Camera Performance</h3>
              <p className="text-slate-400 text-sm">Most active cameras and their uptime</p>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                {topCameras.map((camera, index) => (
                  <div key={index} className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg">
                    <div>
                      <p className="text-white font-medium">{camera.name}</p>
                      <p className="text-slate-400 text-sm">{camera.alerts} alerts this period</p>
                    </div>
                    <div className="text-right">
                      <p className="text-white font-medium">{camera.uptime}%</p>
                      <p className="text-slate-400 text-sm">Uptime</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>

          {/* System Health */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="bg-slate-800 rounded-lg border border-slate-700"
          >
            <div className="p-6 border-b border-slate-700">
              <h3 className="text-lg font-semibold text-white">System Health</h3>
              <p className="text-slate-400 text-sm">Current status of all services</p>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-slate-300">AI Processing</span>
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-green-400 text-sm">Optimal</span>
                  </div>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-slate-300">Database</span>
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-green-400 text-sm">Healthy</span>
                  </div>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-slate-300">Network Latency</span>
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                    <span className="text-yellow-400 text-sm">Elevated</span>
                  </div>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-slate-300">Storage Usage</span>
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-green-400 text-sm">68% Used</span>
                  </div>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-slate-300">CPU Load</span>
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                    <span className="text-blue-400 text-sm">42% Average</span>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>

        {/* Quick Insights */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="mt-8 bg-slate-800 rounded-lg border border-slate-700 p-6"
        >
          <h3 className="text-lg font-semibold text-white mb-4">AI Insights</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="flex items-start space-x-3">
              <div className="w-8 h-8 bg-blue-500/20 rounded-lg flex items-center justify-center mt-1">
                <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <p className="text-white font-medium">Peak Activity Hours</p>
                <p className="text-slate-400 text-sm">Most alerts occur between 2-4 PM on weekdays</p>
              </div>
            </div>
            
            <div className="flex items-start space-x-3">
              <div className="w-8 h-8 bg-green-500/20 rounded-lg flex items-center justify-center mt-1">
                <svg className="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <p className="text-white font-medium">AI Accuracy</p>
                <p className="text-slate-400 text-sm">Detection accuracy has improved 15% this month</p>
              </div>
            </div>
            
            <div className="flex items-start space-x-3">
              <div className="w-8 h-8 bg-yellow-500/20 rounded-lg flex items-center justify-center mt-1">
                <svg className="w-4 h-4 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <div>
                <p className="text-white font-medium">Maintenance Alert</p>
                <p className="text-slate-400 text-sm">Camera 3 requires attention within 7 days</p>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
