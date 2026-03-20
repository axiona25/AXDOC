/** Formati firma (RF-076, RF-077) */
export type SignatureFormat = 'cades' | 'pades_invisible' | 'pades_graphic'

/** Stato richiesta firma */
export type SignatureStatus =
  | 'pending_otp'
  | 'pending_provider'
  | 'completed'
  | 'failed'
  | 'expired'
  | 'rejected'

/** Target tipo (FASE 20) */
export type SignatureTargetType = 'document' | 'protocol' | 'dossier'

/** Step sequenza firma */
export type SequenceStepStatus = 'pending' | 'signed' | 'rejected' | 'skipped'

export interface SignatureSequenceStepItem {
  id: number
  order: number
  signer: string
  signer_email?: string
  role_required: string
  status: SequenceStepStatus
  signed_at?: string
  rejection_reason?: string
  certificate_info?: Record<string, unknown>
}

/** Stato conservazione */
export type ConservationStatus =
  | 'draft'
  | 'pending'
  | 'sent'
  | 'in_progress'
  | 'completed'
  | 'failed'
  | 'rejected'

export interface SignatureRequestItem {
  id: string
  target_type?: SignatureTargetType
  document?: string
  document_version?: string
  document_title?: string
  protocol?: string
  dossier?: string
  requested_by: string
  requested_by_email?: string
  signer?: string
  signer_email?: string
  format: SignatureFormat
  status: SignatureStatus
  signature_reason?: string
  signed_at?: string
  created_at: string
  otp_expires_at?: string
  error_message?: string
  sign_all_documents?: boolean
  signed_document_ids?: string[]
  signature_sequence?: unknown[]
  current_signer_index?: number
  require_sequential?: boolean
  sequence_steps?: SignatureSequenceStepItem[]
  current_signer?: { id: string; email: string }
}

export interface ConservationRequestItem {
  id: string
  document: string
  document_title?: string
  document_version: string
  status: ConservationStatus
  document_type: string
  document_date: string
  reference_number?: string
  conservation_class: string
  submitted_at?: string
  completed_at?: string
  certificate_url?: string
  error_message?: string
  created_at: string
}

export interface RequestSignatureForm {
  signer_id: string
  format: SignatureFormat
  reason?: string
  location?: string
  graphic_signature?: string
}

export interface VerifyOTPForm {
  otp_code: string
}

export interface SendToConservationForm {
  document_type: string
  document_date: string
  reference_number?: string
  conservation_class: '1' | '2' | '3'
}
