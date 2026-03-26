import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useBulkSelection } from '../useBulkSelection'

describe('useBulkSelection', () => {
  it('starts empty', () => {
    const { result } = renderHook(() => useBulkSelection())
    expect(result.current.count).toBe(0)
    expect(result.current.hasSelection).toBe(false)
  })

  it('toggle adds and removes', () => {
    const { result } = renderHook(() => useBulkSelection<string>())
    act(() => {
      result.current.toggle('id1')
    })
    expect(result.current.count).toBe(1)
    expect(result.current.isSelected('id1')).toBe(true)
    act(() => {
      result.current.toggle('id1')
    })
    expect(result.current.count).toBe(0)
  })

  it('exposes ids array', () => {
    const { result } = renderHook(() => useBulkSelection<string>())
    act(() => {
      result.current.selectAll(['x', 'y'])
    })
    expect(result.current.ids.sort()).toEqual(['x', 'y'])
  })

  it('selectAll and deselectAll', () => {
    const { result } = renderHook(() => useBulkSelection<string>())
    act(() => {
      result.current.selectAll(['a', 'b', 'c'])
    })
    expect(result.current.count).toBe(3)
    act(() => {
      result.current.deselectAll()
    })
    expect(result.current.count).toBe(0)
  })
})
