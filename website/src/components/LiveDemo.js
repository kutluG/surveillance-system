import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ArrowTopRightOnSquareIcon, PlayIcon } from '@heroicons/react/24/outline';
import { getServiceUrls } from '../config/urls';

export default function LiveDemo() {
  const [systemStatus, setSystemStatus] = useState('connecting');
  const [stats, setStats] = useState({
    activeCameras: 0,
    eventsToday: 0,
    alertsToday: 0,
    uptime: '0%'
  });

  const serviceUrls = getServiceUrls();

  useEffect(() => {
    // Simulate loading system status
    const timer = setTimeout(() => {
      setSystemStatus('online');
      setStats({
        activeCameras: 8,
        eventsToday: 247,
        alertsToday: 12,
        uptime: '99.9%'
      });
    }, 2000);

    return () => clearTimeout(timer);
  }, []);

  const statusColor = systemStatus === 'online' ? 'text-green-500' : 
                     systemStatus === 'offline' ? 'text-red-500' : 'text-yellow-500';

  return (
    <div className="py-16 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-3xl md:text-4xl font-bold text-gray-900 mb-4"
          >
            Live System Demo
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-xl text-gray-600 max-w-3xl mx-auto"
          >
            Experience our surveillance system in action. Real monitoring dashboards 
            and system analytics running live.
          </motion.p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          {/* Left side - Live dashboard */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6 }}
            className="bg-gray-900 rounded-2xl p-6 text-white"
          >
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-semibold">System Dashboard</h3>
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${systemStatus === 'online' ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`}></div>
                <span className={`text-sm font-medium ${statusColor}`}>
                  {systemStatus.charAt(0).toUpperCase() + systemStatus.slice(1)}
                </span>
              </div>
            </div>

            {/* Stats grid */}
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="text-2xl font-bold text-blue-400">{stats.activeCameras}</div>
                <div className="text-gray-400 text-sm">Active Cameras</div>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="text-2xl font-bold text-green-400">{stats.eventsToday}</div>
                <div className="text-gray-400 text-sm">Events Today</div>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="text-2xl font-bold text-yellow-400">{stats.alertsToday}</div>
                <div className="text-gray-400 text-sm">Alerts Today</div>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="text-2xl font-bold text-purple-400">{stats.uptime}</div>
                <div className="text-gray-400 text-sm">Uptime</div>
              </div>
            </div>

            {/* Recent activity */}
            <div className="space-y-3">
              <h4 className="text-sm font-medium text-gray-300 mb-2">Recent Activity</h4>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-300">Motion detected - Camera 3</span>
                  <span className="text-gray-500">2m ago</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-300">Alert sent - Unauthorized access</span>
                  <span className="text-gray-500">5m ago</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-300">System health check - All OK</span>
                  <span className="text-gray-500">10m ago</span>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Right side - Access links */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="space-y-6"
          >
            <div>
              <h3 className="text-2xl font-bold text-gray-900 mb-4">
                Access Live System
              </h3>
              <p className="text-gray-600 mb-6">
                Explore our running surveillance system with full monitoring capabilities, 
                real-time analytics, and API documentation.
              </p>
            </div>            <div className="space-y-4">
              {/* Grafana Dashboard */}
              <a
                href={serviceUrls.grafana}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-between p-4 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-lg hover:from-orange-600 hover:to-red-600 transition-colors group"
              >
                <div>
                  <div className="font-semibold">Grafana Dashboard</div>
                  <div className="text-orange-100 text-sm">Real-time monitoring & analytics</div>                </div>
                <ArrowTopRightOnSquareIcon className="w-5 h-5 group-hover:scale-110 transition-transform" />
              </a>

              {/* Prometheus Metrics */}
              <a
                href={serviceUrls.prometheus}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-between p-4 bg-gradient-to-r from-blue-500 to-indigo-500 text-white rounded-lg hover:from-blue-600 hover:to-indigo-600 transition-colors group"
              >
                <div>
                  <div className="font-semibold">Prometheus Metrics</div>
                  <div className="text-blue-100 text-sm">System metrics & performance</div>                </div>
                <ArrowTopRightOnSquareIcon className="w-5 h-5 group-hover:scale-110 transition-transform" />
              </a>

              {/* API Documentation */}
              <a
                href={serviceUrls.docs}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-between p-4 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-lg hover:from-green-600 hover:to-emerald-600 transition-colors group"
              >
                <div>
                  <div className="font-semibold">API Documentation</div>
                  <div className="text-green-100 text-sm">Interactive API explorer</div>
                </div>                <ArrowTopRightOnSquareIcon className="w-5 h-5 group-hover:scale-110 transition-transform" />
              </a>

              {/* Internal Dashboard */}
              <button className="w-full flex items-center justify-between p-4 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg hover:from-purple-600 hover:to-pink-600 transition-colors group">
                <div>
                  <div className="font-semibold">Web Dashboard</div>
                  <div className="text-purple-100 text-sm">Camera feeds & alerts</div>
                </div>
                <PlayIcon className="w-5 h-5 group-hover:scale-110 transition-transform" />
              </button>
            </div>

            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
              <div className="text-sm text-gray-600">
                <strong>Note:</strong> These are live links to the actual running system. 
                Grafana credentials: admin/admin
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
