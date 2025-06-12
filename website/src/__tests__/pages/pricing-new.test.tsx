import { render, fireEvent } from '@testing-library/react'
import { ThemeProvider } from '@/components/theme-provider'
import PricingPage from '@/app/pricing/page'

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

describe('Pricing Page', () => {
  it('renders pricing page correctly', () => {
    const { container } = renderWithTheme(<PricingPage />)
    expect(container).toMatchSnapshot()
  })

  it('displays pricing plans', () => {
    const { getByText } = renderWithTheme(<PricingPage />)
    expect(getByText('Basic')).toBeInTheDocument()
    expect(getByText('Pro')).toBeInTheDocument()
    expect(getByText('Enterprise')).toBeInTheDocument()
  })

  it('displays monthly pricing by default', () => {
    const { getByText } = renderWithTheme(<PricingPage />)
    // Check for price numbers
    expect(getByText('199')).toBeInTheDocument()
    expect(getByText('499')).toBeInTheDocument()
    expect(getByText('999')).toBeInTheDocument()
  })

  it('toggles to yearly pricing when switched', () => {
    const { getByText, getByRole } = renderWithTheme(<PricingPage />)
    
    // Find and click the yearly toggle
    const yearlyToggle = getByRole('switch')
    fireEvent.click(yearlyToggle)
    
    // Check if yearly prices are displayed
    expect(getByText('1990')).toBeInTheDocument()
    expect(getByText('4990')).toBeInTheDocument()
    expect(getByText('9990')).toBeInTheDocument()
  })
})
