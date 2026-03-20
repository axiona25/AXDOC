import { api } from './api'
import type {
  SignatureRequestItem,
  ConservationRequestItem,
  RequestSignatureForm,
  SendToConservationForm,
} from '../types/signatures'

export function requestSignature(docId: string, data: RequestSignatureForm): Promise<{ signature_request_id: string; otp_message: string }> {
  return api
    .post<{ signature_request_id: string; otp_message: string }>(`/api/documents/${docId}/request_signature/`, data)
    .then((r) => r.data)
}

/** FASE 20: richiesta firma su protocollo */
export function requestForProtocol(data: {
  protocol_id: string
  signers: Array<{ user_id: string; order?: number; role_required?: string }>
  signature_type?: string
  require_sequential?: boolean
  sign_all_documents?: boolean
  notes?: string
}): Promise<SignatureRequestItem> {
  return api.post<SignatureRequestItem>('/api/signatures/request_for_protocol/', data).then((r) => r.data)
}

/** FASE 20: richiesta firma su fascicolo */
export function requestForDossier(data: {
  dossier_id: string
  signers: Array<{ user_id: string; order?: number; role_required?: string }>
  signature_type?: string
  require_sequential?: boolean
  sign_all_documents?: boolean
  notes?: string
}): Promise<SignatureRequestItem> {
  return api.post<SignatureRequestItem>('/api/signatures/request_for_dossier/', data).then((r) => r.data)
}

/** FASE 20: firma step corrente */
export function signStep(id: string, data?: { certificate_b64?: string; timestamp_b64?: string; pin?: string; certificate_info?: Record<string, unknown> }): Promise<SignatureRequestItem> {
  return api.post<SignatureRequestItem>(`/api/signatures/${id}/sign_step/`, data ?? {}).then((r) => r.data)
}

/** FASE 20: rifiuta step */
export function rejectStep(id: string, reason: string): Promise<SignatureRequestItem> {
  return api.post<SignatureRequestItem>(`/api/signatures/${id}/reject_step/`, { reason }).then((r) => r.data)
}

/** FASE 20: stato completo con sequence_steps */
export function getStatusDetail(id: string): Promise<SignatureRequestItem> {
  return api.get<SignatureRequestItem>(`/api/signatures/${id}/status_detail/`).then((r) => r.data)
}

/** FASE 20: download file firmato (o ZIP) */
export function downloadSigned(id: string): Promise<Blob> {
  return api.get(`/api/signatures/${id}/download_signed/`, { responseType: 'blob' }).then((r) => r.data)
}

/** FASE 20: lista richieste per target (targetId opzionale: se omesso ritorna tutte per quel tipo) */
export function getSignaturesByTarget(
  targetType: 'document' | 'protocol' | 'dossier',
  targetId?: string
): Promise<SignatureRequestItem[]> {
  const params: Record<string, string> = { target_type: targetType }
  if (targetId) params.target_id = targetId
  return api
    .get<{ results?: SignatureRequestItem[] }>('/api/signatures/', { params })
    .then((r) => (Array.isArray(r.data) ? r.data : (r.data?.results ?? [])))
}

export function verifyOtp(sigId: string, otp: string): Promise<{ success: boolean; message: string }> {
  return api.post<{ success: boolean; message: string }>(`/api/signatures/${sigId}/verify_otp/`, { otp_code: otp }).then((r) => r.data)
}

export function resendOtp(sigId: string): Promise<{ message: string }> {
  return api.post<{ message: string }>(`/api/signatures/${sigId}/resend_otp/`).then((r) => r.data)
}

export function getDocumentSignatures(docId: string): Promise<SignatureRequestItem[]> {
  return api.get<SignatureRequestItem[]>(`/api/documents/${docId}/signatures/`).then((r) => r.data)
}

export function verifySignatureValidity(sigId: string): Promise<{ valid: boolean; signer_name?: string; signed_at?: string; certificate_info?: Record<string, unknown> }> {
  return api.get(`/api/signatures/${sigId}/verify/`).then((r) => r.data)
}

export function sendToConservation(docId: string, data: SendToConservationForm): Promise<{ conservation_request_id: string; status: string }> {
  return api
    .post<{ conservation_request_id: string; status: string }>(`/api/documents/${docId}/send_to_conservation/`, data)
    .then((r) => r.data)
}

export function checkConservationStatus(consId: string): Promise<ConservationRequestItem> {
  return api.post<ConservationRequestItem>(`/api/conservation/${consId}/check_status/`).then((r) => r.data)
}

export function getDocumentConservation(docId: string): Promise<ConservationRequestItem[]> {
  return api.get<ConservationRequestItem[]>(`/api/documents/${docId}/conservation/`).then((r) => r.data)
}
