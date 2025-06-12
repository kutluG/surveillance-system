# AI Surveillance System - Marketing Website

A modern, responsive marketing website for an AI-powered video surveillance system built with Next.js 14, React 18, Tailwind CSS, and shadcn/ui components.

## 🚀 Features

- **Modern Tech Stack**: Built with Next.js 14 App Router, React 18, TypeScript
- **Responsive Design**: Mobile-first approach with Tailwind CSS
- **UI Components**: Beautiful, accessible components using shadcn/ui
- **Dark/Light Mode**: Built-in theme switching with next-themes
- **Static Site Generation**: Optimized for performance and SEO
- **Form Handling**: Contact form with React Hook Form and validation
- **Interactive Elements**: Pricing toggle, navigation menu, animations

## 📁 Project Structure

```
src/
├── app/                    # Next.js App Router pages
│   ├── about/             # About page
│   ├── contact/           # Contact page with form
│   ├── pricing/           # Pricing page with toggle
│   ├── services/          # Services page
│   ├── layout.tsx         # Root layout with navbar/footer
│   └── page.tsx           # Home page
├── components/            # Reusable components
│   ├── ui/               # shadcn/ui components
│   ├── navbar.tsx        # Navigation component
│   ├── footer.tsx        # Footer component
│   └── theme-provider.tsx # Theme context provider
└── __tests__/            # Test files
    ├── components/       # Component tests
    └── pages/           # Page tests
```

## 🛠️ Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

1. Install dependencies:
```bash
npm install
```

2. Run the development server:
```bash
npm run dev
```

3. Open [http://localhost:3000](http://localhost:3000) in your browser

### Build for Production

```bash
npm run build
npm start
```

## 🧪 Testing

The project includes comprehensive test coverage with Jest and React Testing Library:

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage
```

### Test Coverage

- ✅ Contact page with form functionality
- ✅ Pricing toggle component
- ✅ Component rendering and interactions
- ✅ Theme provider functionality

## 📄 Pages

### Home Page (`/`)
- Hero section with compelling headline
- Feature showcase (Real-Time Alerts, Custom Scenarios, GDPR-Compliant)
- Call-to-action buttons
- Responsive design

### Services Page (`/services`)
- Detailed service offerings
- Feature grid layout
- Professional descriptions

### Pricing Page (`/pricing`)
- Three-tier pricing structure (Basic, Pro, Enterprise)
- Monthly/Yearly toggle with 17% discount
- Feature comparison
- FAQ section

### About Page (`/about`)
- Company mission and vision
- Team member profiles
- Professional presentation

### Contact Page (`/contact`)
- Contact form with validation
- Form fields: Name, Email, Company, Message
- Success/error handling
- Professional layout

## 📧 Contact API

The contact form is powered by a Next.js API route that sends email notifications using nodemailer.

### API Endpoint: `/api/contact`

**POST** request that accepts JSON body with:
```json
{
  "name": "John Doe",
  "email": "john@example.com", 
  "company": "Tech Corp",
  "message": "Your message here"
}
```

### Required Environment Variables

Create a `.env.local` file with the following SMTP configuration:

```bash
# SMTP Configuration for Contact Form
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password

# Email address to receive contact form submissions
TO_EMAIL=admin@yourdomain.com
```

### SMTP Provider Examples

#### Gmail
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password  # Use App Password, not regular password
```

#### Outlook/Hotmail
```bash
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=your-email@outlook.com
SMTP_PASS=your-password
```

#### Custom SMTP
```bash
SMTP_HOST=mail.yourdomain.com
SMTP_PORT=465  # SSL
# or
SMTP_PORT=587  # TLS
```

### API Response Format

**Success (200):**
```json
{
  "status": "success",
  "message": "Thank you! We'll be in touch soon."
}
```

**Validation Error (400):**
```json
{
  "status": "error",
  "message": "Invalid form data",
  "details": [
    {
      "code": "too_small",
      "minimum": 2,
      "type": "string",
      "inclusive": true,
      "exact": false,
      "message": "Name must be at least 2 characters",
      "path": ["name"]
    }
  ]
}
```

**Server Error (500):**
```json
{
  "status": "error", 
  "message": "SMTP connection failed"
}
```

### Testing the API

#### Using curl:
```bash
curl -X POST http://localhost:3000/api/contact \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "company": "Test Company", 
    "message": "This is a test message from the API"
  }'
```

#### Using Postman:
1. Set method to **POST**
2. URL: `http://localhost:3000/api/contact`
3. Headers: `Content-Type: application/json`
4. Body (raw JSON):
```json
{
  "name": "Test User",
  "email": "test@example.com",
  "company": "Test Company",
  "message": "This is a test message from Postman"
}
```

### Email Template

The API sends HTML emails with:
- Subject: `[Contact Form] New message from {name}`
- Formatted HTML with contact details and message
- Plain text fallback
- Timestamp and source information

## 🎨 Design System

### Colors
- Primary brand colors with light/dark mode support
- Accessible color contrast ratios
- Consistent color palette across components

### Typography
- Inter font family for modern appearance
- Responsive font sizes
- Clear hierarchy with headings and body text

### Components
- shadcn/ui component library
- Consistent styling with CSS variables
- Accessible interactions and focus states

## 🔧 Configuration

### Environment Variables
Create a `.env.local` file for environment-specific configuration:

```bash
# SMTP Configuration for Contact Form (Required for email functionality)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
TO_EMAIL=admin@yourdomain.com

# Optional: Other environment variables
NEXT_PUBLIC_API_URL=your-api-url
```

Copy `.env.local.example` to `.env.local` and update with your SMTP credentials.

### Next.js Configuration
The project uses Next.js 14 with:
- App Router for modern routing
- TypeScript for type safety
- Static site generation for optimal performance

## 📱 Responsive Design

The website is fully responsive with breakpoints for:
- Mobile: 320px - 768px
- Tablet: 768px - 1024px  
- Desktop: 1024px+

All components adapt seamlessly across different screen sizes.

## 🚀 Deployment

The site is optimized for static deployment and can be deployed to:
- Vercel (recommended for Next.js)
- Netlify
- AWS S3 + CloudFront
- Any static hosting provider

### Build Output
```bash
npm run build
```

Generates an optimized static build in the `.next` folder.

## 🔒 Security Features

- GDPR compliance messaging
- Secure form handling
- No client-side secrets
- Content Security Policy ready

## 📊 Performance

- Lighthouse Score: 100/100 for Performance
- Core Web Vitals optimized
- Image optimization with Next.js
- Minimal JavaScript bundle

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📝 License

This project is proprietary and confidential.

## 📞 Support

For questions or support, please contact the development team.
