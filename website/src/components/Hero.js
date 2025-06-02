import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  PlayIcon, 
  CameraIcon, 
  CpuChipIcon, 
  BellAlertIcon,
  ChartBarIcon,
  ShieldCheckIcon 
} from '@heroicons/react/24/outline';

export default function Hero() {
  return (
    <div className="relative bg-gradient-to-br from-primary-900 via-primary-800 to-primary-700 overflow-hidden">
      {/* Background pattern */}
      <div className="absolute inset-0 bg-black opacity-50"></div>
      <div className="absolute inset-0">
        <div className="absolute inset-0 bg-gradient-to-r from-primary-800/20 to-transparent"></div>
        <svg className="absolute bottom-0 left-0 w-full h-24 text-gray-50" fill="currentColor" viewBox="0 0 1200 120" preserveAspectRatio="none">
          <path d="M321.39,56.44c58-10.79,114.16-30.13,172-41.86,82.39-16.72,168.19-17.73,250.45-.39C823.78,31,906.67,72,985.66,92.83c70.05,18.48,146.53,26.09,214.34,3V0H0V27.35A600.21,600.21,0,0,0,321.39,56.44Z"></path>
        </svg>
      </div>

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 lg:py-32">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          {/* Left column - Content */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center lg:text-left"
          >
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6">
              AI-Powered
              <span className="block text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-400">
                Surveillance
              </span>
              System
            </h1>
            
            <p className="text-xl text-gray-200 mb-8 max-w-lg mx-auto lg:mx-0">
              Enterprise-grade video monitoring with real-time AI analysis, intelligent alerting, 
              and comprehensive analytics. Built for modern security needs.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start mb-12">
              <Link to="/dashboard" className="btn-primary text-lg px-8 py-3 inline-flex items-center">
                <PlayIcon className="w-5 h-5 mr-2" />
                View Live Demo
              </Link>
              <Link to="/docs" className="btn-secondary bg-white/10 text-white border-white/20 hover:bg-white/20 text-lg px-8 py-3">
                Documentation
              </Link>
            </div>

            {/* Key features */}
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
              <div className="flex items-center text-gray-300">
                <CameraIcon className="w-4 h-4 mr-2 text-blue-400" />
                Real-time Processing
              </div>
              <div className="flex items-center text-gray-300">
                <CpuChipIcon className="w-4 h-4 mr-2 text-green-400" />
                AI Detection
              </div>
              <div className="flex items-center text-gray-300">
                <BellAlertIcon className="w-4 h-4 mr-2 text-yellow-400" />
                Smart Alerts
              </div>
              <div className="flex items-center text-gray-300">
                <ChartBarIcon className="w-4 h-4 mr-2 text-purple-400" />
                Analytics
              </div>
              <div className="flex items-center text-gray-300">
                <ShieldCheckIcon className="w-4 h-4 mr-2 text-red-400" />
                Enterprise Security
              </div>
            </div>
          </motion.div>

          {/* Right column - Visual */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="relative"
          >
            <div className="relative bg-white/10 backdrop-blur-sm rounded-2xl p-6 border border-white/20">
              {/* Mock dashboard */}
              <div className="bg-gray-900 rounded-lg p-4 mb-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                    <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                    <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                  </div>
                  <span className="text-gray-400 text-xs">Live Dashboard</span>
                </div>
                
                {/* Mock video feeds */}
                <div className="grid grid-cols-2 gap-2 mb-3">
                  <div className="bg-gray-800 rounded aspect-video flex items-center justify-center">
                    <CameraIcon className="w-8 h-8 text-gray-600" />
                  </div>
                  <div className="bg-gray-800 rounded aspect-video flex items-center justify-center">
                    <CameraIcon className="w-8 h-8 text-gray-600" />
                  </div>
                </div>
                
                {/* Mock alerts */}
                <div className="space-y-2">
                  <div className="flex items-center space-x-2 text-xs">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                    <span className="text-green-400">Camera 1: Normal activity</span>
                  </div>
                  <div className="flex items-center space-x-2 text-xs">
                    <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse"></div>
                    <span className="text-yellow-400">Camera 2: Motion detected</span>
                  </div>
                </div>
              </div>
              
              {/* Status indicators */}
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="bg-green-500/20 rounded-lg p-2">
                  <div className="text-green-400 font-semibold text-sm">8</div>
                  <div className="text-green-300 text-xs">Active Cameras</div>
                </div>
                <div className="bg-blue-500/20 rounded-lg p-2">
                  <div className="text-blue-400 font-semibold text-sm">24/7</div>
                  <div className="text-blue-300 text-xs">Monitoring</div>
                </div>
                <div className="bg-purple-500/20 rounded-lg p-2">
                  <div className="text-purple-400 font-semibold text-sm">AI</div>
                  <div className="text-purple-300 text-xs">Analysis</div>
                </div>
              </div>
            </div>
            
            {/* Floating elements */}
            <motion.div
              animate={{ y: [0, -10, 0] }}
              transition={{ duration: 3, repeat: Infinity }}
              className="absolute -top-4 -right-4 bg-green-500 text-white px-3 py-1 rounded-full text-sm font-medium"
            >
              Live
            </motion.div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
