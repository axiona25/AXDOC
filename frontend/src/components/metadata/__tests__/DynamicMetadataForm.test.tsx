import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DynamicMetadataForm } from '../DynamicMetadataForm'
import type { MetadataStructure } from '../../../types/metadata'

const baseStructure: MetadataStructure = {
  id: 's1',
  name: 'Test',
  description: '',
  allowed_file_extensions: [],
  is_active: true,
  created_at: '',
  updated_at: '',
  fields: [
    {
      id: 'f1',
      name: 'campo_testo',
      label: 'Campo testo',
      field_type: 'text',
      is_required: true,
      is_searchable: true,
      order: 0,
      options: [],
      default_value: null,
      validation_rules: {},
      help_text: '',
    },
    {
      id: 'f2',
      name: 'campo_numero',
      label: 'Numero',
      field_type: 'number',
      is_required: false,
      is_searchable: true,
      order: 1,
      options: [],
      default_value: null,
      validation_rules: { min: 0, max: 100 },
      help_text: '',
    },
    {
      id: 'f3',
      name: 'campo_select',
      label: 'Select',
      field_type: 'select',
      is_required: false,
      is_searchable: true,
      order: 2,
      options: [{ value: 'a', label: 'A' }, { value: 'b', label: 'B' }],
      default_value: null,
      validation_rules: {},
      help_text: '',
    },
    {
      id: 'f4',
      name: 'campo_bool',
      label: 'Booleano',
      field_type: 'boolean',
      is_required: false,
      is_searchable: true,
      order: 3,
      options: [],
      default_value: null,
      validation_rules: {},
      help_text: '',
    },
  ],
}

describe('DynamicMetadataForm', () => {
  it('renders all field types', () => {
    const onChange = vi.fn()
    render(
      <DynamicMetadataForm
        structure={baseStructure}
        values={{}}
        onChange={onChange}
      />
    )
    expect(screen.getByLabelText(/Campo testo/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Numero/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Select/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Booleano/)).toBeInTheDocument()
  })

  it('shows required asterisk for required fields', () => {
    render(
      <DynamicMetadataForm
        structure={baseStructure}
        values={{}}
        onChange={() => {}}
      />
    )
    const label = screen.getByText(/Campo testo/)
    expect(label.parentElement?.textContent).toContain('*')
  })

  it('shows validation errors when provided', () => {
    render(
      <DynamicMetadataForm
        structure={baseStructure}
        values={{ campo_testo: '' }}
        onChange={() => {}}
        errors={{ campo_testo: 'Campo obbligatorio.' }}
      />
    )
    expect(screen.getByRole('alert')).toHaveTextContent('Campo obbligatorio.')
  })

  it('calls onChange when text field changes', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(
      <DynamicMetadataForm
        structure={baseStructure}
        values={{}}
        onChange={onChange}
      />
    )
    const input = screen.getByLabelText(/Campo testo/)
    await user.type(input, 'hello')
    expect(onChange).toHaveBeenCalled()
  })
})
