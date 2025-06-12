"use client"

import { useState } from "react"
import type { Metadata } from "next"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Check } from "lucide-react"
import Link from "next/link"

const plans = [
  {
    name: "Basic",
    description: "Perfect for small businesses and single locations",
    monthlyPrice: 199,
    yearlyPrice: 1990,
    features: [
      "Up to 5 cameras",
      "Real-time AI monitoring",
      "Basic alert notifications",
      "7-day video retention",
      "Email support",
      "Standard dashboard",
      "GDPR compliance",
    ],
  },
  {
    name: "Pro",
    description: "Ideal for growing businesses with multiple locations",
    monthlyPrice: 499,
    yearlyPrice: 4990,
    popular: true,
    features: [
      "Up to 25 cameras",
      "Advanced AI analytics",
      "Custom alert scenarios",
      "30-day video retention",
      "Priority support",
      "Advanced dashboards",
      "Multi-user management",
      "API access",
      "Custom integrations",
    ],
  },
  {
    name: "Enterprise",
    description: "For large organizations with complex requirements",
    monthlyPrice: 999,
    yearlyPrice: 9990,
    features: [
      "Unlimited cameras",
      "Full AI suite",
      "Custom AI models",
      "Configurable retention",
      "24/7 dedicated support",
      "White-label options",
      "Advanced analytics",
      "SLA guarantees",
      "On-premise deployment",
      "Custom development",
    ],
  },
]

export default function PricingPage() {
  const [isYearly, setIsYearly] = useState(false)

  return (
    <div className="flex flex-col">
      {/* Hero Section */}
      <section className="relative bg-gradient-to-b from-background to-muted/20 px-6 py-24 sm:py-32 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
            Simple, Transparent Pricing
          </h1>
          <p className="mt-6 text-lg leading-8 text-muted-foreground">
            Choose the perfect plan for your security needs. All plans include our core AI surveillance features.
          </p>
        </div>
      </section>

      {/* Pricing Toggle */}
      <section className="py-8">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="flex items-center justify-center space-x-4">
            <Label htmlFor="pricing-toggle" className="text-sm font-medium">
              Monthly
            </Label>
            <Switch
              id="pricing-toggle"
              checked={isYearly}
              onCheckedChange={setIsYearly}
            />
            <Label htmlFor="pricing-toggle" className="text-sm font-medium">
              Yearly
              <span className="ml-1.5 inline-flex items-center rounded-full bg-primary/10 px-2 py-1 text-xs font-medium text-primary">
                Save 17%
              </span>
            </Label>
          </div>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="pb-24 sm:pb-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
            {plans.map((plan, index) => (
              <Card 
                key={index} 
                className={`relative ${plan.popular ? 'ring-2 ring-primary shadow-lg scale-105' : ''}`}
              >
                {plan.popular && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                    <span className="inline-flex items-center rounded-full bg-primary px-4 py-1 text-sm font-medium text-primary-foreground">
                      Most Popular
                    </span>
                  </div>
                )}
                <CardHeader className="text-center">
                  <CardTitle className="text-xl">{plan.name}</CardTitle>
                  <CardDescription className="mt-2">
                    {plan.description}
                  </CardDescription>
                  <div className="mt-6">
                    <span className="text-4xl font-bold text-foreground">
                      ${isYearly ? plan.yearlyPrice : plan.monthlyPrice}
                    </span>
                    <span className="text-sm text-muted-foreground">
                      /{isYearly ? 'year' : 'month'}
                    </span>
                  </div>
                  {isYearly && (
                    <p className="text-sm text-muted-foreground">
                      ${Math.round(plan.yearlyPrice / 12)}/month billed annually
                    </p>
                  )}
                </CardHeader>
                <CardContent className="space-y-4">
                  <ul className="space-y-3">
                    {plan.features.map((feature, featureIndex) => (
                      <li key={featureIndex} className="flex items-center space-x-3">
                        <Check className="h-5 w-5 text-primary flex-shrink-0" />
                        <span className="text-sm text-muted-foreground">{feature}</span>
                      </li>
                    ))}
                  </ul>
                  <div className="pt-6">
                    <Button 
                      className="w-full" 
                      variant={plan.popular ? "default" : "outline"}
                      asChild
                    >
                      <Link href="/contact">Select Plan</Link>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="bg-muted/50 py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Frequently Asked Questions
            </h2>
          </div>
          <div className="mx-auto mt-16 max-w-2xl space-y-8">            <div>
              <h3 className="text-lg font-semibold text-foreground">
                Can I upgrade or downgrade my plan?
              </h3>
              <p className="mt-2 text-muted-foreground">
                Yes, you can change your plan at any time. Upgrades take effect immediately, 
                while downgrades take effect at the next billing cycle.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-foreground">
                What payment methods do you accept?
              </h3>
              <p className="mt-2 text-muted-foreground">
                We accept all major credit cards (Visa, MasterCard, American Express), 
                PayPal, and bank transfers for annual plans.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-foreground">
                Is there a free trial available?
              </h3>
              <p className="mt-2 text-muted-foreground">
                Yes, we offer a 14-day free trial for all plans. No credit card required to start.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-foreground">
                What happens to my data if I cancel?
              </h3>
              <p className="mt-2 text-muted-foreground">
                Your data is retained for 30 days after cancellation, giving you time to export 
                any important information. After 30 days, all data is permanently deleted.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-foreground">
                Do you offer custom enterprise solutions?
              </h3>
              <p className="mt-2 text-muted-foreground">
                Yes, our Enterprise plan includes custom development and on-premise deployment options. 
                Contact us to discuss your specific requirements.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Ready to secure your business?
            </h2>
            <p className="mx-auto mt-6 max-w-xl text-lg leading-8 text-muted-foreground">
              Start your free trial today and experience the power of AI-driven surveillance.
            </p>
            <div className="mt-10 flex items-center justify-center gap-x-6">
              <Button size="lg" asChild>
                <Link href="/contact">Start Free Trial</Link>
              </Button>
              <Button variant="outline" size="lg" asChild>
                <Link href="/contact">Contact Sales</Link>
              </Button>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
