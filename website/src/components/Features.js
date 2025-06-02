import React from 'react';
import { motion } from 'framer-motion';
import {
  CpuChipIcon,
  BellAlertIcon,
  ChartBarIcon,
  ShieldCheckIcon,
  CameraIcon,
  ServerIcon
} from '@heroicons/react/24/outline';

const features = [
  {
    name: 'Real-time Video Processing',
    description: 'Process multiple camera feeds simultaneously with low-latency AI analysis and instant object detection.',
    icon: CameraIcon,
    color: 'text-blue-600',
    bgColor: 'bg-blue-100'
  },
  {
    name: 'AI-Powered Detection',
    description: 'Advanced machine learning models for object detection, activity recognition, and behavioral analysis.',
    icon: CpuChipIcon,
    color: 'text-green-600',
    bgColor: 'bg-green-100'
  },
  {
    name: 'Intelligent Alerting',
    description: 'Smart notification system with multi-channel delivery via email, SMS, Slack, and custom webhooks.',
    icon: BellAlertIcon,
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-100'
  },
  {
    name: 'Comprehensive Analytics',
    description: 'Real-time dashboards, historical data analysis, and performance metrics with Grafana integration.',
    icon: ChartBarIcon,
    color: 'text-purple-600',
    bgColor: 'bg-purple-100'
  },
  {
    name: 'Scalable Architecture',
    description: 'Microservices-based design with Docker containers, supporting horizontal scaling and high availability.',
    icon: ServerIcon,
    color: 'text-indigo-600',
    bgColor: 'bg-indigo-100'
  },
  {
    name: 'Enterprise Security',
    description: 'Built-in authentication, encryption, audit logging, and compliance with enterprise security standards.',
    icon: ShieldCheckIcon,
    color: 'text-red-600',
    bgColor: 'bg-red-100'
  }
];

export default function Features() {
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
            Enterprise-Grade Features
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-xl text-gray-600 max-w-3xl mx-auto"
          >
            Built with modern technologies and best practices, our surveillance system 
            delivers production-ready capabilities for organizations of any size.
          </motion.p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <motion.div
              key={feature.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
              className="relative p-6 bg-white rounded-xl shadow-lg border border-gray-100 hover:shadow-xl transition-shadow duration-300"
            >
              <div className="flex items-center mb-4">
                <div className={`p-2 rounded-lg ${feature.bgColor}`}>
                  <feature.icon className={`w-6 h-6 ${feature.color}`} />
                </div>
              </div>
              
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                {feature.name}
              </h3>
              
              <p className="text-gray-600 leading-relaxed">
                {feature.description}
              </p>
              
              {/* Hover effect */}
              <div className="absolute inset-0 rounded-xl border-2 border-transparent hover:border-primary-200 transition-colors duration-300"></div>
            </motion.div>
          ))}
        </div>

        {/* Statistics */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="mt-16 bg-gradient-to-r from-primary-600 to-primary-700 rounded-2xl p-8 text-white"
        >
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 text-center">
            <div>
              <div className="text-3xl font-bold mb-2">8+</div>
              <div className="text-primary-200">Microservices</div>
            </div>
            <div>
              <div className="text-3xl font-bold mb-2">24/7</div>
              <div className="text-primary-200">Monitoring</div>
            </div>
            <div>
              <div className="text-3xl font-bold mb-2">99.9%</div>
              <div className="text-primary-200">Uptime</div>
            </div>
            <div>
              <div className="text-3xl font-bold mb-2">∞</div>
              <div className="text-primary-200">Scalability</div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
