// src/components/DownloadButton.test.jsx
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import DownloadButton from './DownloadButton';

describe('DownloadButton', () => {
  test('renders the button with the default label', () => {
    render(<DownloadButton url="/fake-report.xlsx" />);
    expect(screen.getByRole('link', { name: /Download Excel Report/i })).toBeInTheDocument();
  });

  test('renders the button with a custom label', () => {
    render(<DownloadButton url="/fake-report.xlsx" label="Download Custom Data" />);
    expect(screen.getByRole('link', { name: /Download Custom Data/i })).toBeInTheDocument();
  });

  test('has the correct href attribute', () => {
    const testUrl = '/path/to/report.xlsx';
    render(<DownloadButton url={testUrl} />);
    expect(screen.getByRole('link')).toHaveAttribute('href', testUrl);
  });

  test('is disabled and shows alert if URL is not provided', () => {
    window.alert = jest.fn(); // Mock window.alert
    render(<DownloadButton />);
    const button = screen.getByRole('link');
    expect(button).toHaveClass('disabled');
    expect(button).toHaveAttribute('aria-disabled', 'true');

    fireEvent.click(button);
    expect(window.alert).toHaveBeenCalledWith('Download link is not available or report is not ready yet.');
    window.alert.mockClear(); // Clear mock for other tests
  });

   test('is enabled if URL is provided', () => {
    render(<DownloadButton url="/real-url.xlsx" />);
    const button = screen.getByRole('link');
    expect(button).not.toHaveClass('disabled');
    expect(button).toHaveAttribute('aria-disabled', 'false');
  });
});