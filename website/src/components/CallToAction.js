import React from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';

export default function CallToAction() {
  return (
    <section className="py-24 bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 relative overflow-hidden">
      {/* Background Effects */}
      <div className="absolute inset-0">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl animate-pulse-slow"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse-slow delay-1000"></div>
      </div>

      <div className="container mx-auto px-6 relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="text-center max-w-4xl mx-auto"
        >
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6">
            Ready to Secure Your
            <span className="block text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-400">
              Digital Perimeter?
            </span>
          </h2>
          
          <p className="text-xl text-slate-300 mb-12 leading-relaxed">
            Join hundreds of organizations already using our AI-powered surveillance system 
            to protect their assets with enterprise-grade security and real-time monitoring.
          </p>

          <div className="flex flex-col sm:flex-row gap-6 justify-center items-center">
            <motion.div
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Link
                to="/dashboard"
                className="inline-flex items-center px-8 py-4 bg-gradient-to-r from-blue-600 to-cyan-600 text-white font-semibold rounded-lg hover:from-blue-700 hover:to-cyan-700 transition-all duration-300 shadow-lg hover:shadow-2xl group"
              >
                <span>Start Free Trial</span>
                <svg className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </Link>
            </motion.div>

            <motion.div
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Link
                to="/documentation"
                className="inline-flex items-center px-8 py-4 border-2 border-slate-600 text-slate-300 font-semibold rounded-lg hover:border-blue-500 hover:text-white transition-all duration-300 group"
              >
                <span>View Documentation</span>
                <svg className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </Link>
            </motion.div>
          </div>

          {/* Trust Indicators */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            viewport={{ once: true }}
            className="mt-16 pt-8 border-t border-slate-700"
          >
            <p className="text-slate-400 text-sm mb-6">Trusted by industry leaders</p>
            <div className="flex flex-wrap justify-center items-center gap-8 opacity-60">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-slate-700 rounded"></div>
                <span className="text-slate-400 font-medium">TechCorp</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-slate-700 rounded"></div>
                <span className="text-slate-400 font-medium">SecureInc</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-slate-700 rounded"></div>
                <span className="text-slate-400 font-medium">DataGuard</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-slate-700 rounded"></div>
                <span className="text-slate-400 font-medium">CloudShield</span>
              </div>
            </div>
          </motion.div>

          {/* Contact Info */}
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.5 }}
            viewport={{ once: true }}
            className="mt-12 text-center"
          >
            <p className="text-slate-400 text-sm">
              Need enterprise support? Contact us at{' '}
              <a href="mailto:enterprise@surveillanceai.com" className="text-blue-400 hover:text-blue-300 transition-colors">
                enterprise@surveillanceai.com
              </a>
            </p>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
