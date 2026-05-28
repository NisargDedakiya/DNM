import { AxiosError } from 'axios'

export interface OperationalError {
  message: string
  status?: number
  code?: string
  details?: any
}

export function handleApiError(error: unknown): OperationalError {
  const operationalError: OperationalError = {
    message: 'An unexpected operational error occurred.',
  }

  if (error instanceof AxiosError) {
    operationalError.status = error.response?.status
    operationalError.code = error.code
    
    const responseData = error.response?.data
    if (responseData && typeof responseData === 'object') {
      operationalError.message = responseData.detail || responseData.message || operationalError.message
      operationalError.details = responseData.errors || responseData.details
    } else {
      operationalError.message = error.message
    }
  } else if (error instanceof Error) {
    operationalError.message = error.message
  }

  console.error('[API Error Handler] Parsed error:', operationalError)
  return operationalError
}

export default handleApiError
