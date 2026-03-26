import { describe, it, expect, beforeEach } from 'vitest'
import { act } from '@testing-library/react'
import { useToastStore } from '../store/toastStore'

describe('toastStore', () => {
  beforeEach(() => {
    act(() => {
      useToastStore.getState().clearAll()
    })
  })

  it('addToast adds a toast', () => {
    act(() => {
      useToastStore.getState().addToast({
        title: 'Test',
        message: 'Hello',
        notification_type: 'info',
        link_url: '',
      })
    })
    expect(useToastStore.getState().toasts.length).toBe(1)
  })

  it('max 3 toasts', () => {
    act(() => {
      for (let i = 0; i < 5; i++) {
        useToastStore.getState().addToast({
          title: `Toast ${i}`,
          message: '',
          notification_type: 'info',
          link_url: '',
        })
      }
    })
    expect(useToastStore.getState().toasts.length).toBe(3)
  })

  it('clearAll removes all toasts', () => {
    act(() => {
      useToastStore.getState().addToast({
        title: 'A',
        message: '',
        notification_type: 'info',
        link_url: '',
      })
      useToastStore.getState().clearAll()
    })
    expect(useToastStore.getState().toasts.length).toBe(0)
  })

  it('removeToast removes specific toast', () => {
    act(() => {
      useToastStore.getState().addToast({
        title: 'Remove me',
        message: '',
        notification_type: 'info',
        link_url: '',
      })
    })
    const id = useToastStore.getState().toasts[0].id
    act(() => {
      useToastStore.getState().removeToast(id)
    })
    expect(useToastStore.getState().toasts.length).toBe(0)
  })
})
