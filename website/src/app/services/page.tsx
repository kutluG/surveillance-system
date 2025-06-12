import type { Metadata } from "next"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { 
  Cpu, 
  Brain, 
  Headphones, 
  Cloud, 
  Lock, 
  BarChart3, 
  Zap, 
  Users, 
  Settings 
} from "lucide-react"
import Link from "next/link"

export const metadata: Metadata = {
  title: "Services",
  description: "Comprehensive AI surveillance services including edge deployment, intelligent insights, and 24/7 support.",
}

const services = [
  {
    icon: Cpu,
    title: "Edge AI Deployment",
    description: "Deploy our AI models directly on your existing camera infrastructure for real-time processing with minimal latency and maximum privacy."
  },
  {
    icon: Brain,
    title: "Agent-Driven Insights",
    description: "Advanced AI agents that continuously learn from your environment, providing actionable insights and predictive analytics for proactive security."
  },
  {
    icon: Headphones,
    title: "Integration & Support",
    description: "Seamless integration with existing VMS systems and 24/7 expert support to ensure your security infrastructure operates at peak performance."
  },
  {
    icon: Cloud,
    title: "Cloud Analytics",
    description: "Secure cloud-based analytics platform for centralized monitoring, reporting, and advanced data analysis across multiple locations."
  },
  {
    icon: Lock,
    title: "Privacy Protection",
    description: "Built-in face anonymization, data encryption, and configurable retention policies to ensure complete GDPR and privacy law compliance."
  },
  {
    icon: BarChart3,
    title: "Custom Dashboards",
    description: "Personalized dashboards and reporting tools that provide clear visibility into security metrics, trends, and operational insights."
  },
  {
    icon: Zap,
    title: "Real-Time Processing",
    description: "Lightning-fast AI processing that delivers instant alerts and responses to security events as they happen, not after the fact."
  },
  {
    icon: Users,
    title: "Multi-User Management",
    description: "Role-based access control and user management system that allows different team members to access relevant information securely."
  },
  {
    icon: Settings,
    title: "Custom Configuration",
    description: "Flexible configuration options to tailor the AI surveillance system to your specific security needs, policies, and operational requirements."
  },
]

export default function ServicesPage() {
  return (
    <div className="flex flex-col">
      {/* Hero Section */}
      <section className="relative bg-gradient-to-b from-background to-muted/20 px-6 py-24 sm:py-32 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
            Our Services
          </h1>
          <p className="mt-6 text-lg leading-8 text-muted-foreground">
            Comprehensive AI surveillance solutions designed to meet your security needs. 
            From edge deployment to cloud analytics, we&apos;ve got you covered.
          </p>
        </div>
      </section>

      {/* Services Grid */}
      <section className="py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
            {services.map((service, index) => {
              const IconComponent = service.icon
              return (
                <Card key={index} className="relative overflow-hidden">
                  <CardHeader>
                    <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 mb-4">
                      <IconComponent className="h-6 w-6 text-primary" />
                    </div>
                    <CardTitle className="text-xl">{service.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <CardDescription className="text-sm leading-6">
                      {service.description}
                    </CardDescription>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </div>
      </section>

      {/* Process Section */}
      <section className="bg-muted/50 py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              How It Works
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Simple deployment process that gets you up and running quickly
            </p>
          </div>
          <div className="mx-auto mt-16 max-w-2xl sm:mt-20 lg:mt-24 lg:max-w-none">
            <dl className="grid max-w-xl grid-cols-1 gap-x-8 gap-y-16 lg:max-w-none lg:grid-cols-3">
              <div className="flex flex-col items-center text-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary text-primary-foreground font-bold text-xl mb-4">
                  1
                </div>
                <dt className="text-lg font-semibold leading-7 text-foreground">
                  Assessment & Planning
                </dt>
                <dd className="mt-2 text-base leading-7 text-muted-foreground">
                  We analyze your current infrastructure and security requirements to design 
                  the optimal AI surveillance solution for your needs.
                </dd>
              </div>
              <div className="flex flex-col items-center text-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary text-primary-foreground font-bold text-xl mb-4">
                  2
                </div>
                <dt className="text-lg font-semibold leading-7 text-foreground">
                  Deployment & Integration
                </dt>
                <dd className="mt-2 text-base leading-7 text-muted-foreground">
                  Our experts handle the complete deployment and integration with your existing 
                  systems, ensuring minimal disruption to your operations.
                </dd>
              </div>
              <div className="flex flex-col items-center text-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary text-primary-foreground font-bold text-xl mb-4">
                  3
                </div>
                <dt className="text-lg font-semibold leading-7 text-foreground">
                  Training & Support
                </dt>
                <dd className="mt-2 text-base leading-7 text-muted-foreground">
                  Comprehensive training for your team and ongoing 24/7 support to ensure 
                  you get the maximum value from your AI surveillance system.
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Ready to get started?
            </h2>
            <p className="mx-auto mt-6 max-w-xl text-lg leading-8 text-muted-foreground">
              Contact our experts to discuss your specific requirements and get a customized solution.
            </p>
            <div className="mt-10 flex items-center justify-center gap-x-6">
              <Button size="lg" asChild>
                <Link href="/contact">Get a Quote</Link>
              </Button>
              <Button variant="outline" size="lg" asChild>
                <Link href="/pricing">View Pricing</Link>
              </Button>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
