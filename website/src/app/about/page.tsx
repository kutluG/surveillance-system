import type { Metadata } from "next"
import Image from "next/image"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Linkedin } from "lucide-react"
import Link from "next/link"

export const metadata: Metadata = {
  title: "About",
  description: "Learn about SecureWatch AI's mission, team, and commitment to revolutionizing video surveillance with artificial intelligence.",
}

const team = [
  {
    name: "Sarah Chen",
    role: "CEO & Co-founder",
    bio: "Former Google AI researcher with 10+ years in computer vision and machine learning. Led the development of large-scale surveillance systems for smart cities.",
    image: "/images/team/sarah-chen.jpg",
    linkedin: "https://linkedin.com/in/sarahchen",
  },
  {
    name: "Marcus Rodriguez",
    role: "CTO & Co-founder",
    bio: "Ex-Microsoft Principal Engineer specializing in edge computing and real-time AI systems. Expert in deploying AI at scale across distributed infrastructures.",
    image: "/images/team/marcus-rodriguez.jpg",
    linkedin: "https://linkedin.com/in/marcusrodriguez",
  },
  {
    name: "Dr. Emily Watson",
    role: "Head of AI Research",
    bio: "PhD in Computer Vision from Stanford. Published 50+ papers on object detection and behavioral analysis. Former research scientist at Tesla Autopilot.",
    image: "/images/team/emily-watson.jpg",
    linkedin: "https://linkedin.com/in/emilywatson",
  },
  {
    name: "David Kim",
    role: "VP of Security",
    bio: "Cybersecurity veteran with expertise in privacy-preserving technologies and GDPR compliance. Former security architect at Apple and Signal.",
    image: "/images/team/david-kim.jpg",
    linkedin: "https://linkedin.com/in/davidkim",
  },
]

export default function AboutPage() {
  return (
    <div className="flex flex-col">
      {/* Hero Section */}
      <section className="relative bg-gradient-to-b from-background to-muted/20 px-6 py-24 sm:py-32 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
            About SecureWatch AI
          </h1>
          <p className="mt-6 text-lg leading-8 text-muted-foreground">
            We&apos;re on a mission to make intelligent video surveillance accessible, 
            privacy-focused, and incredibly effective for organizations of all sizes.
          </p>
        </div>
      </section>

      {/* Mission Section */}
      <section className="py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto grid max-w-2xl grid-cols-1 gap-x-8 gap-y-16 lg:mx-0 lg:max-w-none lg:grid-cols-2 lg:items-start">
            <div>
              <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
                Our Mission
              </h2>
              <p className="mt-6 text-lg leading-8 text-muted-foreground">
                Traditional video surveillance systems are reactive, requiring human operators to 
                watch endless hours of footage. We believe security should be proactive, intelligent, 
                and respect privacy rights.
              </p>
              <p className="mt-6 text-lg leading-8 text-muted-foreground">
                Our AI-powered platform transforms passive cameras into intelligent sentries that 
                understand context, learn from environments, and provide actionable insights in 
                real-time while maintaining the highest standards of privacy and compliance.
              </p>
            </div>
            <div className="lg:pl-8">
              <div className="space-y-8">
                <div>
                  <h3 className="text-xl font-semibold text-foreground">Privacy First</h3>
                  <p className="mt-2 text-muted-foreground">
                    Built with privacy by design, featuring face anonymization, end-to-end encryption, 
                    and configurable data retention policies.
                  </p>
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-foreground">Edge Intelligence</h3>
                  <p className="mt-2 text-muted-foreground">
                    Our AI runs locally on your infrastructure, ensuring fast response times and 
                    keeping your sensitive data under your control.
                  </p>
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-foreground">Continuous Learning</h3>
                  <p className="mt-2 text-muted-foreground">
                    Our systems adapt and improve over time, learning the unique patterns of your 
                    environment to reduce false alarms and increase accuracy.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Team Section */}
      <section className="bg-muted/50 py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Meet Our Team
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              World-class experts in AI, computer vision, and security technology
            </p>
          </div>
          <div className="mx-auto mt-16 grid max-w-2xl grid-cols-1 gap-8 sm:grid-cols-2 lg:mx-0 lg:max-w-none lg:grid-cols-4">
            {team.map((person, index) => (
              <Card key={index} className="bg-background">
                <CardHeader className="text-center pb-2">
                  <div className="mx-auto h-32 w-32 rounded-full bg-muted flex items-center justify-center mb-4">
                    <span className="text-4xl font-bold text-muted-foreground">
                      {person.name.split(' ').map(n => n[0]).join('')}
                    </span>
                  </div>
                  <h3 className="text-lg font-semibold text-foreground">{person.name}</h3>
                  <p className="text-sm text-primary font-medium">{person.role}</p>
                </CardHeader>
                <CardContent className="text-center">
                  <p className="text-sm text-muted-foreground leading-relaxed mb-4">
                    {person.bio}
                  </p>
                  <Link 
                    href={person.linkedin} 
                    className="inline-flex items-center text-primary hover:text-primary/80 transition-colors"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <Linkedin className="h-4 w-4" />
                    <span className="sr-only">LinkedIn profile for {person.name}</span>
                  </Link>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Company Stats */}
      <section className="py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Our Impact
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Numbers that showcase our commitment to excellence
            </p>
          </div>
          <div className="mx-auto mt-16 grid max-w-2xl grid-cols-1 gap-8 lg:mx-0 lg:max-w-none lg:grid-cols-4">
            <div className="text-center">
              <div className="text-4xl font-bold text-primary">500+</div>
              <div className="mt-2 text-lg font-semibold text-foreground">Organizations Protected</div>
              <div className="mt-1 text-sm text-muted-foreground">Across 50+ countries</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-primary">10M+</div>
              <div className="mt-2 text-lg font-semibold text-foreground">Hours Monitored</div>
              <div className="mt-1 text-sm text-muted-foreground">Every month</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-primary">99.9%</div>
              <div className="mt-2 text-lg font-semibold text-foreground">Uptime</div>
              <div className="mt-1 text-sm text-muted-foreground">Guaranteed SLA</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-primary">95%</div>
              <div className="mt-2 text-lg font-semibold text-foreground">Accuracy Rate</div>
              <div className="mt-1 text-sm text-muted-foreground">AI detection precision</div>
            </div>
          </div>
        </div>
      </section>

      {/* Values Section */}
      <section className="bg-muted/50 py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Our Values
            </h2>
          </div>
          <div className="mx-auto mt-16 max-w-2xl sm:mt-20 lg:mt-24 lg:max-w-none">
            <dl className="grid max-w-xl grid-cols-1 gap-x-8 gap-y-16 lg:max-w-none lg:grid-cols-3">
              <div className="flex flex-col items-center text-center">
                <dt className="text-lg font-semibold leading-7 text-foreground mb-2">
                  Innovation
                </dt>
                <dd className="text-base leading-7 text-muted-foreground">
                  We continuously push the boundaries of what&apos;s possible with AI and computer vision, 
                  staying at the forefront of technology advancement.
                </dd>
              </div>
              <div className="flex flex-col items-center text-center">
                <dt className="text-lg font-semibold leading-7 text-foreground mb-2">
                  Transparency
                </dt>
                <dd className="text-base leading-7 text-muted-foreground">
                  We believe in clear communication, honest pricing, and explainable AI systems 
                  that our customers can understand and trust.
                </dd>
              </div>
              <div className="flex flex-col items-center text-center">
                <dt className="text-lg font-semibold leading-7 text-foreground mb-2">
                  Security
                </dt>
                <dd className="text-base leading-7 text-muted-foreground">
                  Security isn&apos;t just our product—it&apos;s our obsession. We apply the same rigorous 
                  standards to protecting our platform as we do to protecting our customers.
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </section>
    </div>
  )
}
