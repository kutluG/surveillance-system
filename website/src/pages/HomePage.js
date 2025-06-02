import React from 'react';
import Hero from '../components/Hero';
import Features from '../components/Features';
import TechStack from '../components/TechStack';
import LiveDemo from '../components/LiveDemo';
import CallToAction from '../components/CallToAction';

export default function HomePage() {
  return (
    <div>
      <Hero />
      <Features />
      <TechStack />
      <LiveDemo />
      <CallToAction />
    </div>
  );
}
