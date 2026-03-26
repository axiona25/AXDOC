import { describe, it, expect, beforeEach } from 'vitest'
import { act } from '@testing-library/react'
import { useNotificationRealtimeStore } from '../store/notificationRealtimeStore'

describe('notificationRealtimeStore', () => {
  beforeEach(() => {
    act(() => {
      useNotificationRealtimeStore.setState({ unreadCount: 0, wsConnected: false })
    })
  })

  it('setUnreadCount updates count', () => {
    act(() => {
      useNotificationRealtimeStore.getState().setUnreadCount(7)
    })
    expect(useNotificationRealtimeStore.getState().unreadCount).toBe(7)
  })

  it('setWsConnected updates flag', () => {
    act(() => {
      useNotificationRealtimeStore.getState().setWsConnected(true)
    })
    expect(useNotificationRealtimeStore.getState().wsConnected).toBe(true)
  })

  it('can set unread and ws together', () => {
    act(() => {
      useNotificationRealtimeStore.setState({ unreadCount: 5, wsConnected: true })
    })
    const s = useNotificationRealtimeStore.getState()
    expect(s.unreadCount).toBe(5)
    expect(s.wsConnected).toBe(true)
  })
})
