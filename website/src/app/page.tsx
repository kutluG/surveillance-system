import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { AlertTriangle, Eye, Shield } from "lucide-react"

export default function HomePage() {
  return (
    <div className="flex flex-col">
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-b from-background to-muted/20 px-6 py-24 sm:py-32 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-6xl">
            AI-Powered Video Surveillance,{" "}
            <span className="text-primary">Simplified</span>
          </h1>
          <p className="mt-6 text-lg leading-8 text-muted-foreground">
            Transform your security infrastructure with intelligent monitoring that understands context, 
            detects threats in real-time, and adapts to your unique requirements while maintaining 
            complete privacy compliance.
          </p>
          <div className="mt-10 flex items-center justify-center gap-x-6">
            <Button asChild size="lg">
              <Link href="/contact">Get Started</Link>
            </Button>
            <Button variant="outline" size="lg" asChild>
              <Link href="/services">Learn More</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Why Choose SecureWatch AI?
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Our advanced AI technology provides unmatched security monitoring capabilities
            </p>
          </div>
          <div className="mx-auto mt-16 max-w-2xl sm:mt-20 lg:mt-24 lg:max-w-none">
            <dl className="grid max-w-xl grid-cols-1 gap-x-8 gap-y-16 lg:max-w-none lg:grid-cols-3">
              <Card className="flex flex-col items-center text-center p-6">
                <CardHeader>
                  <div className="flex h-16 w-16 items-center justify-center rounded-lg bg-primary/10 mx-auto mb-4">
                    <AlertTriangle className="h-8 w-8 text-primary" />
                  </div>
                  <CardTitle className="text-xl">Real-Time Alerts</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-center">
                    Get instant notifications when our AI detects unusual activities, threats, or 
                    custom scenarios you&apos;ve configured. No more watching hours of footage.
                  </CardDescription>
                </CardContent>
              </Card>

              <Card className="flex flex-col items-center text-center p-6">
                <CardHeader>
                  <div className="flex h-16 w-16 items-center justify-center rounded-lg bg-primary/10 mx-auto mb-4">
                    <Eye className="h-8 w-8 text-primary" />
                  </div>
                  <CardTitle className="text-xl">Custom Scenarios</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-center">
                    Define specific behaviors, objects, or patterns you want to monitor. Our AI 
                    learns your environment and adapts to your unique security requirements.
                  </CardDescription>
                </CardContent>
              </Card>

              <Card className="flex flex-col items-center text-center p-6">
                <CardHeader>
                  <div className="flex h-16 w-16 items-center justify-center rounded-lg bg-primary/10 mx-auto mb-4">
                    <Shield className="h-8 w-8 text-primary" />
                  </div>
                  <CardTitle className="text-xl">GDPR-Compliant</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-center">
                    Built with privacy by design. Face anonymization, data encryption, and 
                    configurable retention policies ensure complete compliance with privacy regulations.
                  </CardDescription>
                </CardContent>
              </Card>
            </dl>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-muted/50 py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Ready to upgrade your security?
            </h2>
            <p className="mx-auto mt-6 max-w-xl text-lg leading-8 text-muted-foreground">
              Join hundreds of organizations already using SecureWatch AI to protect what matters most.
            </p>
            <div className="mt-10 flex items-center justify-center gap-x-6">
              <Button size="lg" asChild>
                <Link href="/contact">Start Free Trial</Link>
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
