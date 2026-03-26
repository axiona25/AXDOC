import { useId, useState } from 'react'
import { Dialog, DialogTitle } from '@headlessui/react'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { changePasswordRequired } from '../../services/authService'

const schema = z
  .object({
    new_password: z
      .string()
      .min(8, 'Minimo 8 caratteri')
      .regex(/[A-Z]/, 'Almeno una maiuscola')
      .regex(/\d/, 'Almeno un numero'),
    confirm_password: z.string(),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: 'Le password non coincidono',
    path: ['confirm_password'],
  })

type FormData = z.infer<typeof schema>

interface ChangePasswordModalProps {
  isOpen: boolean
  onSuccess: () => void
}

export function ChangePasswordModal({ isOpen, onSuccess }: ChangePasswordModalProps) {
  const titleId = useId()
  const trapRef = useFocusTrap(isOpen)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isValid },
    reset,
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { new_password: '', confirm_password: '' },
    mode: 'onChange',
  })

  const onSubmit = async (data: FormData) => {
    setError(null)
    try {
      await changePasswordRequired(data.new_password, data.confirm_password)
      reset()
      onSuccess()
    } catch (err: unknown) {
      const res = (err as { response?: { data?: { new_password?: string[]; detail?: string } } })
        ?.response
      const msg =
        res?.data?.new_password?.[0] ?? res?.data?.detail ?? 'Errore durante il cambio password.'
      setError(msg)
    }
  }

  return (
    <Dialog open={isOpen} onClose={() => {}} className="relative z-50">
      <div className="fixed inset-0 bg-black/50" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel
          ref={trapRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          className="mx-auto w-full max-w-md rounded-lg bg-white p-6 shadow-xl"
        >
          <DialogTitle id={titleId} className="text-lg font-semibold text-slate-800">
            Cambio password obbligatorio
          </DialogTitle>
          <p className="mt-1 text-sm text-slate-600">
            È necessario cambiare la password temporanea prima di continuare.
          </p>

          <form onSubmit={handleSubmit(onSubmit)} className="mt-4 space-y-4">
            <div>
              <label
                htmlFor="new_password"
                className="mb-1 block text-sm font-medium text-slate-700"
              >
                Nuova password <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <input
                  id="new_password"
                  type={showNewPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  className="w-full rounded border border-slate-300 px-3 py-2 pr-10 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  {...register('new_password')}
                />
                <button
                  type="button"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-700"
                  tabIndex={-1}
                >
                  {showNewPassword ? (
                    <svg
                      className="h-5 w-5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
                      />
                    </svg>
                  ) : (
                    <svg
                      className="h-5 w-5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                      />
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                      />
                    </svg>
                  )}
                </button>
              </div>
              {errors.new_password && (
                <p className="mt-1 text-sm text-red-600">{errors.new_password.message}</p>
              )}
              <p className="mt-1 text-xs text-slate-500">
                Requisiti: minimo 8 caratteri, almeno 1 maiuscola, 1 numero
              </p>
            </div>

            <div>
              <label
                htmlFor="confirm_password"
                className="mb-1 block text-sm font-medium text-slate-700"
              >
                Conferma password <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <input
                  id="confirm_password"
                  type={showConfirmPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  className="w-full rounded border border-slate-300 px-3 py-2 pr-10 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  {...register('confirm_password')}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-700"
                  tabIndex={-1}
                >
                  {showConfirmPassword ? (
                    <svg
                      className="h-5 w-5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
                      />
                    </svg>
                  ) : (
                    <svg
                      className="h-5 w-5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                      />
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                      />
                    </svg>
                  )}
                </button>
              </div>
              {errors.confirm_password && (
                <p className="mt-1 text-sm text-red-600">{errors.confirm_password.message}</p>
              )}
            </div>

            {error && <div className="rounded bg-red-50 p-2 text-sm text-red-700">{error}</div>}

            <button
              type="submit"
              disabled={!isValid}
              className="w-full rounded bg-indigo-600 py-2 font-medium text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cambia password
            </button>
          </form>
        </Dialog.Panel>
      </div>
    </Dialog>
  )
}
