import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';

export default function PricingPage() {
  const [billingPeriod, setBillingPeriod] = useState('monthly');

  const plans = [
    {
      name: 'Starter',
      description: 'Perfect for small businesses and home security',
      price: billingPeriod === 'monthly' ? 99 : 990,
      cameras: '1-5 cameras',
      storage: '100GB cloud storage',
      features: [
        'Real-time monitoring',
        'Basic AI detection',
        'Email alerts',
        'Mobile app access',
        'Standard support',
        '30-day recording history'
      ],
      highlight: false,
      popular: false
    },
    {
      name: 'Professional',
      description: 'Advanced features for growing businesses',
      price: billingPeriod === 'monthly' ? 299 : 2990,
      cameras: '6-25 cameras',
      storage: '500GB cloud storage',
      features: [
        'Everything in Starter',
        'Advanced AI analytics',
        'Multi-channel alerts (SMS, Email, Webhook)',
        'Custom alert rules',
        'API access',
        '90-day recording history',
        'Priority support',
        'User management'
      ],
      highlight: true,
      popular: true
    },
    {
      name: 'Enterprise',
      description: 'Full-scale security solution for large organizations',
      price: billingPeriod === 'monthly' ? 999 : 9990,
      cameras: 'Unlimited cameras',
      storage: 'Unlimited storage',
      features: [
        'Everything in Professional',
        'On-premise deployment',
        'Custom AI model training',
        'Advanced behavior analysis',
        'Integration with existing systems',
        'Unlimited recording history',
        '24/7 dedicated support',
        'SLA guarantee',
        'Custom reporting',
        'White-label solution'
      ],
      highlight: false,
      popular: false
    }
  ];

  const addOns = [
    {
      name: 'Advanced Analytics',
      description: 'Heat maps, people counting, and advanced reporting',
      price: '$49/month'
    },
    {
      name: 'Integration Pack',
      description: 'Pre-built integrations with popular security systems',
      price: '$99/month'
    },
    {
      name: 'Custom AI Training',
      description: 'Train models specific to your environment and needs',
      price: '$299/month'
    },
    {
      name: 'Premium Support',
      description: '24/7 phone support with 1-hour response time',
      price: '$199/month'
    }
  ];

  const faqs = [
    {
      question: 'Can I change my plan at any time?',
      answer: 'Yes, you can upgrade or downgrade your plan at any time. Changes take effect immediately, and billing is prorated.'
    },
    {
      question: 'Is there a free trial available?',
      answer: 'We offer a 14-day free trial for all plans. No credit card required to start your trial.'
    },
    {
      question: 'What happens to my data if I cancel?',
      answer: 'Your data is retained for 30 days after cancellation, giving you time to export or transfer to another service.'
    },
    {
      question: 'Do you offer on-premise deployment?',
      answer: 'Yes, Enterprise customers can deploy SurveillanceAI on their own infrastructure with full control over data.'
    },
    {
      question: 'Is there a setup fee?',
      answer: 'No setup fees for Starter and Professional plans. Enterprise plans may include a one-time implementation fee based on complexity.'
    }
  ];

  return (
    <div className="min-h-screen bg-slate-900 pt-20">
      <div className="container mx-auto px-6 py-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
            Choose Your Security Plan
          </h1>
          <p className="text-xl text-slate-400 max-w-3xl mx-auto">
            Flexible pricing options to match your security needs. Start with our free trial 
            and scale as your organization grows.
          </p>
        </motion.div>

        {/* Billing Toggle */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="flex justify-center mb-12"
        >
          <div className="flex bg-slate-800 rounded-lg p-2 border border-slate-700">
            <button
              onClick={() => setBillingPeriod('monthly')}
              className={`px-6 py-2 rounded-md text-sm font-medium transition-colors ${
                billingPeriod === 'monthly'
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Monthly
            </button>
            <button
              onClick={() => setBillingPeriod('yearly')}
              className={`px-6 py-2 rounded-md text-sm font-medium transition-colors relative ${
                billingPeriod === 'yearly'
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Yearly
              <span className="absolute -top-2 -right-2 bg-green-500 text-white text-xs px-2 py-1 rounded-full">
                Save 20%
              </span>
            </button>
          </div>
        </motion.div>

        {/* Pricing Cards */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16"
        >
          {plans.map((plan, index) => (
            <motion.div
              key={plan.name}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 * index }}
              className={`relative bg-slate-800 rounded-xl border-2 p-8 ${
                plan.highlight
                  ? 'border-blue-500 scale-105'
                  : 'border-slate-700 hover:border-slate-600'
              } transition-all duration-300`}
            >
              {plan.popular && (
                <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                  <span className="bg-blue-600 text-white px-4 py-2 rounded-full text-sm font-medium">
                    Most Popular
                  </span>
                </div>
              )}

              <div className="text-center mb-8">
                <h3 className="text-2xl font-bold text-white mb-2">{plan.name}</h3>
                <p className="text-slate-400 mb-4">{plan.description}</p>
                <div className="mb-4">
                  <span className="text-4xl font-bold text-white">${plan.price}</span>
                  <span className="text-slate-400">/{billingPeriod === 'monthly' ? 'month' : 'year'}</span>
                </div>
                <p className="text-slate-300 font-medium">{plan.cameras}</p>
                <p className="text-slate-400 text-sm">{plan.storage}</p>
              </div>

              <ul className="space-y-3 mb-8">
                {plan.features.map((feature, featureIndex) => (
                  <li key={featureIndex} className="flex items-center space-x-3">
                    <svg className="w-5 h-5 text-green-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    <span className="text-slate-300">{feature}</span>
                  </li>
                ))}
              </ul>

              <Link
                to="/dashboard"
                className={`block w-full text-center py-3 px-6 rounded-lg font-semibold transition-colors ${
                  plan.highlight
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-slate-700 text-white hover:bg-slate-600'
                }`}
              >
                Start Free Trial
              </Link>
            </motion.div>
          ))}
        </motion.div>

        {/* Add-ons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mb-16"
        >
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold text-white mb-4">Add-on Services</h2>
            <p className="text-slate-400">Enhance your security system with additional features</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {addOns.map((addon, index) => (
              <motion.div
                key={addon.name}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 * index }}
                className="bg-slate-800 rounded-lg border border-slate-700 p-6 hover:border-blue-500/50 transition-colors"
              >
                <h3 className="text-lg font-semibold text-white mb-3">{addon.name}</h3>
                <p className="text-slate-400 text-sm mb-4">{addon.description}</p>
                <div className="flex items-center justify-between">
                  <span className="text-blue-400 font-semibold">{addon.price}</span>
                  <button className="text-blue-400 hover:text-blue-300 text-sm font-medium">
                    Add to Plan
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Enterprise CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="bg-gradient-to-r from-blue-600 to-cyan-600 rounded-xl p-8 text-center mb-16"
        >
          <h2 className="text-3xl font-bold text-white mb-4">Need a Custom Solution?</h2>
          <p className="text-blue-100 mb-6 max-w-2xl mx-auto">
            Large organization with specific requirements? Our enterprise team can create 
            a custom solution tailored to your unique security needs.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              to="/documentation"
              className="inline-flex items-center px-6 py-3 bg-white text-blue-600 font-semibold rounded-lg hover:bg-blue-50 transition-colors"
            >
              Schedule Consultation
            </Link>
            <a
              href="mailto:enterprise@surveillanceai.com"
              className="inline-flex items-center px-6 py-3 border-2 border-white text-white font-semibold rounded-lg hover:bg-white hover:text-blue-600 transition-colors"
            >
              Contact Enterprise Sales
            </a>
          </div>
        </motion.div>

        {/* FAQ */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold text-white mb-4">Frequently Asked Questions</h2>
            <p className="text-slate-400">Get answers to common questions about our pricing and features</p>
          </div>

          <div className="max-w-3xl mx-auto space-y-6">
            {faqs.map((faq, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 * index }}
                className="bg-slate-800 rounded-lg border border-slate-700 p-6"
              >
                <h3 className="text-lg font-semibold text-white mb-3">{faq.question}</h3>
                <p className="text-slate-300">{faq.answer}</p>
              </motion.div>
            ))}
          </div>

          <div className="text-center mt-8">
            <p className="text-slate-400 mb-4">Still have questions?</p>
            <a
              href="mailto:support@surveillanceai.com"
              className="inline-flex items-center text-blue-400 hover:text-blue-300 font-medium"
            >
              Contact our support team
              <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </a>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
