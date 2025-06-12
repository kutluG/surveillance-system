import { render, fireEvent } from '@testing-library/react'
import { ThemeProvider } from '@/components/theme-provider'
import { useState } from 'react'
import { Switch } from '@/components/ui/switch'

// Mock next-themes
jest.mock('next-themes', () => ({
  useTheme: () => ({
    theme: 'light',
    setTheme: jest.fn(),
  }),
  ThemeProvider: ({ children }: { children: React.ReactNode }) => children,
}))

// Simple pricing toggle component for testing
const PricingToggle = () => {
  const [isYearly, setIsYearly] = useState(false)
  
  const plans = [
    { name: 'Basic', monthly: 199, yearly: 1990 },
    { name: 'Professional', monthly: 499, yearly: 4990 },
    { name: 'Enterprise', monthly: 999, yearly: 9990 }
  ]

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <span>Monthly</span>
        <Switch
          checked={isYearly}
          onCheckedChange={setIsYearly}
          aria-label="Toggle yearly pricing"
        />
        <span>Yearly</span>
      </div>
      
      <div data-testid="pricing-display">
        {plans.map(plan => (
          <div key={plan.name} data-testid={`plan-${plan.name.toLowerCase()}`}>
            <h3>{plan.name}</h3>
            <p data-testid={`price-${plan.name.toLowerCase()}`}>
              ${isYearly ? plan.yearly : plan.monthly}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

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

describe('Pricing Toggle Component', () => {
  it('displays monthly pricing by default', () => {
    const { getByTestId } = renderWithTheme(<PricingToggle />)
    
    expect(getByTestId('price-basic')).toHaveTextContent('$199')
    expect(getByTestId('price-professional')).toHaveTextContent('$499')
    expect(getByTestId('price-enterprise')).toHaveTextContent('$999')
  })

  it('switches to yearly pricing when toggled', () => {
    const { getByRole, getByTestId } = renderWithTheme(<PricingToggle />)
    
    const toggle = getByRole('switch', { name: 'Toggle yearly pricing' })
    fireEvent.click(toggle)
    
    expect(getByTestId('price-basic')).toHaveTextContent('$1990')
    expect(getByTestId('price-professional')).toHaveTextContent('$4990')
    expect(getByTestId('price-enterprise')).toHaveTextContent('$9990')
  })

  it('switches back to monthly pricing when toggled again', () => {
    const { getByRole, getByTestId } = renderWithTheme(<PricingToggle />)
    
    const toggle = getByRole('switch', { name: 'Toggle yearly pricing' })
    
    // Toggle to yearly
    fireEvent.click(toggle)
    expect(getByTestId('price-basic')).toHaveTextContent('$1990')
    
    // Toggle back to monthly
    fireEvent.click(toggle)
    expect(getByTestId('price-basic')).toHaveTextContent('$199')
  })

  it('toggle is unchecked by default', () => {
    const { getByRole } = renderWithTheme(<PricingToggle />)
    
    const toggle = getByRole('switch', { name: 'Toggle yearly pricing' })
    expect(toggle).not.toBeChecked()
  })

  it('toggle becomes checked when clicked', () => {
    const { getByRole } = renderWithTheme(<PricingToggle />)
    
    const toggle = getByRole('switch', { name: 'Toggle yearly pricing' })
    fireEvent.click(toggle)
    
    expect(toggle).toBeChecked()
  })
})
