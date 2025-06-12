import React from 'react';
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
  },
  {
    name: 'AI-Powered Detection',
    description: 'Advanced machine learning algorithms for accurate person, vehicle, and object detection with minimal false positives.',
    icon: CpuChipIcon,
  },
  {
    name: 'Intelligent Alerting',
    description: 'Smart notification system that learns your preferences and reduces alert fatigue while maintaining security.',
    icon: BellAlertIcon,
  },
  {
    name: 'Advanced Analytics',
    description: 'Comprehensive reporting and analytics dashboard with customizable metrics and trend analysis.',
    icon: ChartBarIcon,
  },
  {
    name: 'Enterprise Security',
    description: 'Bank-grade encryption, role-based access control, and compliance with industry security standards.',
    icon: ShieldCheckIcon,
  },
  {
    name: 'Scalable Infrastructure',
    description: 'Cloud-native architecture that scales from single cameras to enterprise deployments of thousands of feeds.',
    icon: ServerIcon,
  }
];

export default function Features() {
  return (
    <div className="py-24 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold text-gray-900 mb-4">
            Powerful Features for Modern Surveillance
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Our AI-powered surveillance system combines cutting-edge technology with intuitive design 
            to deliver unparalleled security monitoring capabilities.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <div key={feature.name} className="bg-white rounded-lg shadow-lg p-6 border border-gray-100 hover:shadow-xl transition-shadow duration-300">
              <div className="flex items-center mb-4">
                <div className="flex-shrink-0">
                  <feature.icon className="h-8 w-8 text-blue-600" />
                </div>
                <h3 className="ml-3 text-lg font-semibold text-gray-900">{feature.name}</h3>
              </div>
              <p className="text-gray-600">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
