import { describe, it, expect, vi, afterEach } from 'vitest'
import { render } from '@testing-library/react'
import { ScreenReaderAnnouncer, announce } from '../ScreenReaderAnnouncer'

describe('ScreenReaderAnnouncer', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders live region without crashing', () => {
    render(<ScreenReaderAnnouncer />)
    expect(document.getElementById('sr-announcer')).toBeInTheDocument()
  })

  it('announce sets message after timeout', () => {
    vi.useFakeTimers()
    render(<ScreenReaderAnnouncer />)
    announce('Fatto')
    vi.advanceTimersByTime(150)
    expect(document.getElementById('sr-announcer')).toHaveTextContent('Fatto')
  })
})
