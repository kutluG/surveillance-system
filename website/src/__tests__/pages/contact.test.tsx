import { render, fireEvent, waitFor } from '@testing-library/react'
import { ThemeProvider } from '@/components/theme-provider'
import ContactPage from '@/app/contact/page'

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

// Mock fetch for form submission
global.fetch = jest.fn()

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

describe('Contact Page', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders contact page correctly', () => {
    const { container } = renderWithTheme(<ContactPage />)
    expect(container).toMatchSnapshot()
  })

  it('displays contact form', () => {
    const { getByLabelText, getByText } = renderWithTheme(<ContactPage />)
    expect(getByLabelText('Name *')).toBeInTheDocument()
    expect(getByLabelText('Email *')).toBeInTheDocument()
    expect(getByLabelText('Company *')).toBeInTheDocument()
    expect(getByLabelText('Message *')).toBeInTheDocument()
    expect(getByText('Send Message')).toBeInTheDocument()
  })

  it('displays contact information section', () => {
    const { getByText } = renderWithTheme(<ContactPage />)
    expect(getByText('Get in Touch')).toBeInTheDocument()
    expect(getByText('Send us a message')).toBeInTheDocument()
  })

  it('validates form fields', async () => {
    const { getByText, getByRole } = renderWithTheme(<ContactPage />)
    
    const submitButton = getByRole('button', { name: 'Send Message' })
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(getByText('Name must be at least 2 characters')).toBeInTheDocument()
    })
  })

  it('submits form with valid data', async () => {
    const mockResponse = { ok: true, json: async () => ({ success: true }) }
    ;(global.fetch as jest.Mock).mockResolvedValueOnce(mockResponse)

    const { getByLabelText, getByRole } = renderWithTheme(<ContactPage />)
    
    fireEvent.change(getByLabelText('Name *'), { target: { value: 'John Doe' } })
    fireEvent.change(getByLabelText('Email *'), { target: { value: 'john@example.com' } })
    fireEvent.change(getByLabelText('Company *'), { target: { value: 'ACME Corp' } })
    fireEvent.change(getByLabelText('Message *'), { target: { value: 'Test message' } })
    
    const submitButton = getByRole('button', { name: 'Send Message' })
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'John Doe',
          email: 'john@example.com',
          company: 'ACME Corp',
          message: 'Test message'
        })
      })
    })
  })
})
