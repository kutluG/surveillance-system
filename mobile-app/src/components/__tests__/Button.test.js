import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import Button from '../Button';

describe('Button Component', () => {
  it('renders correctly with default props', () => {
    const { getByText } = render(
      <Button title="Test Button" onPress={() => {}} />
    );
    
    expect(getByText('Test Button')).toBeTruthy();
  });

  it('calls onPress when pressed', () => {
    const mockOnPress = jest.fn();
    const { getByText } = render(
      <Button title="Test Button" onPress={mockOnPress} />
    );
    
    fireEvent.press(getByText('Test Button'));
    expect(mockOnPress).toHaveBeenCalledTimes(1);
  });

  it('shows loading state correctly', () => {
    const { getByTestId, queryByText } = render(
      <Button title="Test Button" onPress={() => {}} loading={true} />
    );
    
    expect(getByTestId('loading-indicator')).toBeTruthy();
    expect(queryByText('Test Button')).toBeFalsy();
  });

  it('disables button when disabled prop is true', () => {
    const mockOnPress = jest.fn();
    const { getByText } = render(
      <Button title="Test Button" onPress={mockOnPress} disabled={true} />
    );
    
    const button = getByText('Test Button');
    fireEvent.press(button);
    
    expect(mockOnPress).not.toHaveBeenCalled();
  });

  it('applies correct variant styles', () => {
    const { getByTestId } = render(
      <Button 
        title="Test Button" 
        onPress={() => {}} 
        variant="secondary"
        testID="test-button"
      />
    );
    
    const button = getByTestId('test-button');
    expect(button).toHaveStyle({
      backgroundColor: expect.any(String),
    });
  });
  it('applies correct size styles', () => {
    const { getByTestId } = render(
      <Button 
        title="Test Button" 
        onPress={() => {}} 
        size="large"
        testID="test-button"
      />
    );
    
    const button = getByTestId('test-button');
    expect(button).toHaveStyle({
      minHeight: 56,
    });
  });

  it('renders icon when provided', () => {
    const { getByTestId } = render(
      <Button 
        title="Test Button" 
        onPress={() => {}} 
        icon="home"
      />
    );
    
    expect(getByTestId('button-icon')).toBeTruthy();
  });

  it('meets accessibility requirements', () => {
    const { getByRole } = render(
      <Button 
        title="Test Button" 
        onPress={() => {}} 
        accessibilityLabel="Test Button"
      />
    );
    
    const button = getByRole('button');
    expect(button).toBeTruthy();
    expect(button.props.accessibilityLabel).toBe('Test Button');
  });
});
