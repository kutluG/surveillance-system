import { render } from '@testing-library/react'
import { ThemeProvider } from '@/components/theme-provider'
import HomePage from '@/app/page'

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
  }),
  useSearchParams: () => ({
    get: jest.fn(),
  }),
}))

// Mock next-themes
jest.mock('next-themes', () => ({
  useTheme: () => ({
    theme: 'light',
    setTheme: jest.fn(),
  }),
  ThemeProvider: ({ children }: { children: React.ReactNode }) => children,
}))

const renderWithTheme = (component: React.ReactElement) => {
  return render(
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      {component}
    </ThemeProvider>
  )
}

describe('Home Page', () => {
  it('renders home page correctly', () => {
    const { container } = renderWithTheme(<HomePage />)
    expect(container).toMatchSnapshot()
  })

  it('displays main heading', () => {
    const { getByText } = renderWithTheme(<HomePage />)
    expect(getByText('AI-Powered Video Surveillance,')).toBeInTheDocument()
    expect(getByText('Simplified')).toBeInTheDocument()
  })

  it('displays feature cards', () => {
    const { getByText } = renderWithTheme(<HomePage />)
    expect(getByText('Real-Time Alerts')).toBeInTheDocument()
    expect(getByText('Custom Scenarios')).toBeInTheDocument()
    expect(getByText('GDPR-Compliant')).toBeInTheDocument()
  })

  it('displays call-to-action buttons', () => {
    const { getByText } = renderWithTheme(<HomePage />)
    expect(getByText('Get Started')).toBeInTheDocument()
    expect(getByText('Learn More')).toBeInTheDocument()
  })
})
